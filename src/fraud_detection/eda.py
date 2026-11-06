import argparse
from pathlib import Path
import pandas as pd

def main():
 p=argparse.ArgumentParser();p.add_argument('--data',default='data/raw/paysim.csv');a=p.parse_args()
 df=pd.read_csv(a.data);out=Path('reports');out.mkdir(exist_ok=True)
 summary={'transactions':len(df),'fraud_count':int(df.isFraud.sum()),'fraud_rate':float(df.isFraud.mean()),'missing_cells':int(df.isna().sum().sum())}
 pd.DataFrame([summary]).to_csv(out/'dataset_summary.csv',index=False)
 df.groupby('type',dropna=False).agg(transactions=('isFraud','size'),fraud_count=('isFraud','sum')).to_csv(out/'transaction_types.csv')
 print(summary)
if __name__=='__main__':main()
