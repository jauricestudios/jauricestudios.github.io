"""Reproducible exploratory B6 event-model benchmarking.
Input: exported model mart; NO point-in-time B6 source-publication verification.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, SplineTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

root=Path(__file__).resolve().parents[1]
data_dir=root/'data'
output_dir=root/'results'
df=pd.read_csv(data_dir/'b6_model_benchmark.csv',parse_dates=['settlement_date']).sort_values(['settlement_date','settlement_period']).reset_index(drop=True)
cat=['month','day_of_week','settlement_period']; contin=['wind_forecast_mw','demand_forecast_mw']; target='scottish_downward_boa_event'
cutdate=np.sort(df.settlement_date.unique())[int(df.settlement_date.nunique()*.8)]
tr=df[df.settlement_date<cutdate].copy(); te=df[df.settlement_date>=cutdate].copy()
print('split',str(cutdate),'train',len(tr),'test',len(te),'day count',tr.settlement_date.nunique(),te.settlement_date.nunique())
print('prevalence',tr[target].mean(),te[target].mean())
# Interaction is determined only from source forecast wind and demand, known ex ante.
# Standardization estimated only on training sample through ColumnTransformer.
for d in (tr,te): d['wind_x_demand']=(d.wind_forecast_mw / 10000.0)*(d.demand_forecast_mw/10000.0)

def make_original(with_b6):
    numeric=contin+(['b6_headroom_mw'] if with_b6 else [])
    pre=ColumnTransformer([('cont',StandardScaler(),numeric),('cat',OneHotEncoder(handle_unknown='ignore',drop='first'),cat)])
    return Pipeline([('pre',pre),('model',LogisticRegression(max_iter=2000))]),numeric+cat

def make_nonlinear(with_b6=False,nonlin_b6=False):
    transformers=[('weather_splines',SplineTransformer(n_knots=6,degree=3,include_bias=False,knots='quantile'),contin),
                  ('interaction',StandardScaler(),['wind_x_demand']),
                  ('cat',OneHotEncoder(handle_unknown='ignore',drop='first'),cat)]
    features=contin+['wind_x_demand']+cat
    if with_b6:
        if nonlin_b6:
            transformers.append(('b6_spline',SplineTransformer(n_knots=5,degree=3,include_bias=False,knots='quantile'),['b6_headroom_mw']))
            transformers.append(('b6_limit_regime','passthrough',['b6_limit_10000_flag']))
            features+=['b6_headroom_mw','b6_limit_10000_flag']
        else:
            transformers.append(('b6_linear',StandardScaler(),['b6_headroom_mw']))
            features+=['b6_headroom_mw']
    pre=ColumnTransformer(transformers)
    return Pipeline([('pre',pre),('model',LogisticRegression(max_iter=2000))]),features

specs={'M0 — Original linear baseline':make_original(False),
       'M1 — Original + B6 headroom':make_original(True),
       'M2 — Nonlinear system baseline':make_nonlinear(False),
       'M3 — Nonlinear baseline + linear B6':make_nonlinear(True),
       'M4 — Nonlinear baseline + nonlinear B6':make_nonlinear(True,nonlin_b6=True)}

pred={}; metrics=[]; yt=te[target].to_numpy()
for label,(model,features) in specs.items():
    model.fit(tr[features],tr[target]); p=model.predict_proba(te[features])[:,1]
    pred[label]=p
    row={'Model':label,'ROC_AUC':roc_auc_score(yt,p),'Average_precision':average_precision_score(yt,p),
         'Brier_score':brier_score_loss(yt,p),'Log_loss':log_loss(yt,p)}
    print('RESULT',row,flush=True); metrics.append(row)
res=pd.DataFrame(metrics);res.to_csv(output_dir/'b6_benchmark_results.csv',index=False)

# 10000 regime diagnostic: same fitted model evaluated on a restricted evaluation sample only.
mask=te['b6_limit_10000_flag'].to_numpy()==0
print('10GW evaluation count',int((~mask).sum()),'non10 count',int(mask.sum()))
with open(output_dir/'b6_diagnostic_counts.json','w') as f:
 json.dump({'n_rows':len(df),'n_train':len(tr),'n_test':len(te),'n_train_days':tr.settlement_date.nunique(),
            'n_test_days':te.settlement_date.nunique(),'cut_date':str(pd.Timestamp(cutdate).date()),
            'train_event_rate':tr[target].mean(),'test_event_rate':te[target].mean(),
            'n_test_10000_mw_limit':int((~mask).sum(),)},f,indent=2)
for name in pred:
 p=pred[name]
 print('EXCL10',name, {'AUC':roc_auc_score(yt[mask],p[mask]),'Brier':brier_score_loss(yt[mask],p[mask]),'LogLoss':log_loss(yt[mask],p[mask])})
# daily block bootstrap: resample calendar dates instead of settlement periods
unique_days, day_idx=np.unique(te.settlement_date.to_numpy(),return_inverse=True)
indices=[np.flatnonzero(day_idx==i) for i in range(len(unique_days))]
rs=np.random.default_rng(20261112)
B=500
pairs=[('M1 — Original + B6 headroom','M0 — Original linear baseline'),
       ('M3 — Nonlinear baseline + linear B6','M2 — Nonlinear system baseline'),
       ('M4 — Nonlinear baseline + nonlinear B6','M2 — Nonlinear system baseline'),
       ('M4 — Nonlinear baseline + nonlinear B6','M3 — Nonlinear baseline + linear B6')]
boots={k:{'AUC_delta':[],'Brier_improvement':[],'logloss_improvement':[]} for k in pairs}
for b in range(B):
    sampled=rs.integers(0,len(indices),size=len(indices))
    idx=np.concatenate([indices[i] for i in sampled]); y=yt[idx]
    if len(np.unique(y))!=2: continue
    for (a,b0) in pairs:
        p=pred[a][idx]; q=pred[b0][idx]
        boots[(a,b0)]['AUC_delta'].append(roc_auc_score(y,p)-roc_auc_score(y,q))
        boots[(a,b0)]['Brier_improvement'].append(brier_score_loss(y,q)-brier_score_loss(y,p))
        boots[(a,b0)]['logloss_improvement'].append(log_loss(y,q)-log_loss(y,p))
rows=[]
for (a,b0),vals in boots.items():
 for met,vs in vals.items():
    v=np.array(vs)
    rows.append({'Added_model':a,'Comparator':b0,'Metric':met,'Point_estimate':
                 (roc_auc_score(yt,pred[a])-roc_auc_score(yt,pred[b0]) if met=='AUC_delta' else
                 (brier_score_loss(yt,pred[b0])-brier_score_loss(yt,pred[a]) if met=='Brier_improvement' else log_loss(yt,pred[b0])-log_loss(yt,pred[a]))),
                 'Bootstrap_2.5pct':np.percentile(v,2.5),'Bootstrap_97.5pct':np.percentile(v,97.5),'N_boot':len(v)})
intervals=pd.DataFrame(rows);intervals.to_csv(output_dir/'b6_benchmark_uncertainty.csv',index=False)
print('INTERVALS\n',intervals.to_string(index=False),flush=True)

# Group effects by moderate vs elevated wind based on test period quantiles? For exploratory diagnosis
# cutpoints from training data to avoid looking ahead in bin definitions
q=tr.wind_forecast_mw.quantile([.2,.4,.6,.8]).to_numpy()
wind_group=np.searchsorted(q,te.wind_forecast_mw.to_numpy(),side='right')
rows=[]
for i in range(5):
 pick=(wind_group==i)
 y=yt[pick]
 if len(np.unique(y))<2: continue
 for name in ['M2 — Nonlinear system baseline','M3 — Nonlinear baseline + linear B6','M4 — Nonlinear baseline + nonlinear B6']:
  rows.append({'Wind_bin_training_quintiles':i+1,'Model':name,'N':int(pick.sum()),'Event_rate':float(y.mean()),
   'AUC':roc_auc_score(y,pred[name][pick]),'Brier':brier_score_loss(y,pred[name][pick])})
pd.DataFrame(rows).to_csv(output_dir/'b6_benchmark_wind_strata.csv',index=False)
# Save matched predictions for reproducibility and paired day bootstrap
out=te[['settlement_date','settlement_period','wind_forecast_mw','demand_forecast_mw','b6_limit_mw','b6_headroom_mw',target]].copy()
for k,v in pred.items():out[k]=v
out.to_csv(output_dir/'b6_benchmark_predictions.csv',index=False)
print('COMPLETE')
