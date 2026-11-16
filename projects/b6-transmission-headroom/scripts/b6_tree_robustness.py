import numpy as np,pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
p=Path(__file__).resolve().parents[1]; data_dir=p/'data'; output_dir=p/'results'; d=pd.read_csv(data_dir/'b6_model_benchmark.csv',parse_dates=['settlement_date']).sort_values(['settlement_date','settlement_period'])
cut=np.sort(d.settlement_date.unique())[int(d.settlement_date.nunique()*.8)]
tr=d[d.settlement_date<cut]; te=d[d.settlement_date>=cut]
base=['wind_forecast_mw','demand_forecast_mw','month','day_of_week','settlement_period']
tar='scottish_downward_boa_event'; preds={}
for name,feats in [('Tree baseline',base),('Tree + B6 headroom',base+['b6_headroom_mw'])]:
 model=HistGradientBoostingClassifier(max_iter=250,max_leaf_nodes=15,max_depth=4,learning_rate=.05,min_samples_leaf=100,l2_regularization=10,early_stopping=False,random_state=42)
 model.fit(tr[feats],tr[tar]); pr=model.predict_proba(te[feats])[:,1];preds[name]=pr
 print(name, 'auc',roc_auc_score(te[tar],pr),'AP',average_precision_score(te[tar],pr),'brier',brier_score_loss(te[tar],pr),'logloss',log_loss(te[tar],pr),flush=True)
# paired calendar-day bootstrap
keys=te.settlement_date.to_numpy(); days=np.unique(keys); ids=[np.flatnonzero(keys==dd) for dd in days]; yy=te[tar].to_numpy();rng=np.random.default_rng(20261112)
res=[]
for _ in range(500):
 sel=np.concatenate([ids[i] for i in rng.integers(len(ids),size=len(ids))]); y=yy[sel]
 if len(np.unique(y))<2:continue
 a=preds['Tree + B6 headroom'][sel]; b=preds['Tree baseline'][sel]
 res.append((roc_auc_score(y,a)-roc_auc_score(y,b),brier_score_loss(y,b)-brier_score_loss(y,a),log_loss(y,b)-log_loss(y,a)))
A=np.array(res)
print('tree bootstrap AUC,Brier,LL',np.percentile(A,[2.5,50,97.5],axis=0))
# monthly comparisons for M2/M3
pr=pd.read_csv(output_dir/'b6_benchmark_predictions.csv',parse_dates=['settlement_date']);pr['month_group']=pr.settlement_date.dt.to_period('M').astype(str)
rows=[]
for period,g in pr.groupby('month_group'):
 y=g[tar]
 if y.nunique()<2:continue
 p2=g['M2 — Nonlinear system baseline'];p3=g['M3 — Nonlinear baseline + linear B6']
 rows.append({'month':period,'n':len(g),'event_rate':y.mean(),'AUC_M2':roc_auc_score(y,p2),'AUC_M3':roc_auc_score(y,p3),'AUC_gain':roc_auc_score(y,p3)-roc_auc_score(y,p2),'Brier_gain':brier_score_loss(y,p2)-brier_score_loss(y,p3)})
res=pd.DataFrame(rows);res.to_csv(output_dir/'b6_monthly_diagnostics.csv',index=False);print(res.to_string(index=False))
# Combined output
pd.DataFrame({'settlement_date':te.settlement_date,'settlement_period':te.settlement_period,'event':yy,**preds}).to_csv(output_dir/'b6_tree_predictions.csv',index=False)
