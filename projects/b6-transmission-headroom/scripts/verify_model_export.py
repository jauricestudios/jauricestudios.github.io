"""Read-only integrity check of archived B6 model-ready data and split."""
from pathlib import Path
import pandas as pd

root=Path(__file__).resolve().parents[1]
f=root/'data'/'b6_model_benchmark.csv'
df=pd.read_csv(f,parse_dates=['settlement_date'])
required=['settlement_date','settlement_period','wind_forecast_mw','demand_forecast_mw','b6_headroom_mw','scottish_downward_boa_event','scottish_downward_boa_mw','month','day_of_week']
assert all(k in df.columns for k in required), 'Missing required column'
assert len(df)==31532, f'Unexpected row count: {len(df)}'
assert not df[['settlement_date','settlement_period']].duplicated().any(), 'Duplicate period keys'
assert not df[required].isna().any().any(), 'Missing required values'
assert set(df.scottish_downward_boa_event.unique()).issubset({0,1}), 'Non-binary event target'
assert (df.scottish_downward_boa_mw>=0).all(), 'Unexpected negative downward volume'
assert (df.scottish_downward_boa_event.astype(int)==(df.scottish_downward_boa_mw>0).astype(int)).all(), 'Event/volume definition mismatch'
assert df.settlement_date.nunique()==657, 'Unexpected represented-day count'
train=df[df.settlement_date<pd.Timestamp('2025-10-07')]
test=df[df.settlement_date>=pd.Timestamp('2025-10-07')]
assert (len(train),len(test))==(25198,6334),'Train/eval rows differ'
assert (train.settlement_date.nunique(),test.settlement_date.nunique())==(525,132),'Train/eval days differ'
assert test.settlement_date.max()==pd.Timestamp('2026-04-23'), 'Unexpected final evaluation date'
print('PASS:',len(df),'unique model-ready periods;',len(train),'training,',len(test),'evaluation')
print('NOTE: This does not verify historic B6 release times or raw-to-mart transformations.')
