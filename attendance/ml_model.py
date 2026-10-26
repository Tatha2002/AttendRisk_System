"""Train exclusively from explicit labels; never derive evaluation labels from features."""
from pathlib import Path
import os, pickle
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
NUM=['late_count','absent_count','correction_count','leave_count','average_delay_minutes']
FEATURES=NUM+['department']
ROOT=Path(__file__).resolve().parent.parent
MODEL=ROOT/'artifacts'/'risk.pkl'
def clean(frame):
    frame=frame.copy()
    for col in NUM:
        frame[col]=pd.to_numeric(frame[col],errors='coerce').replace([np.inf,-np.inf],np.nan).clip(lower=0)
    frame['department']=frame['department'].fillna('Unknown').astype(str)
    return frame[FEATURES]
def train(path):
    import json
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    frame=pd.read_csv(path).drop_duplicates()
    if 'risk_label' not in frame: raise ValueError('A reviewed binary risk_label is required')
    y=pd.to_numeric(frame['risk_label'],errors='raise')
    if not set(y.unique())=={0,1}: raise ValueError('Both binary classes are required')
    X=clean(frame)
    Xtrain,Xtest,ytrain,ytest=train_test_split(X,y,stratify=y,test_size=.25,random_state=42)
    # Learn outlier caps on training data only.
    caps=Xtrain[NUM].quantile(.99); Xtrain=Xtrain.copy(); Xtest=Xtest.copy()
    Xtrain[NUM]=Xtrain[NUM].clip(upper=caps,axis=1); Xtest[NUM]=Xtest[NUM].clip(upper=caps,axis=1)
    results={}; models={}
    for name,algorithm in [('logistic',LogisticRegression(max_iter=1000,random_state=42)),('forest',RandomForestClassifier(n_estimators=100,random_state=42,class_weight='balanced'))]:
        pre=ColumnTransformer([('numbers',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),NUM),('department',OneHotEncoder(handle_unknown='ignore'),['department'])])
        pipe=Pipeline([('preprocessing',pre),('classifier',algorithm)])
        pipe.fit(Xtrain,ytrain)
        results[name]={'report':classification_report(ytest,pipe.predict(Xtest),output_dict=True,zero_division=0),'roc_auc':roc_auc_score(ytest,pipe.predict_proba(Xtest)[:,1])}
        models[name]=pipe
    best=max(results,key=lambda name:results[name]['roc_auc'])
    MODEL.parent.mkdir(exist_ok=True)
    # Only load artifacts generated locally by this script.
    with MODEL.open('wb') as out: pickle.dump({'pipeline':models[best],'caps':caps},out)
    (MODEL.parent/'metrics.json').write_text(json.dumps({'selected':best,'synthetic_demo_only':True,'models':results},indent=2))
    frame[NUM].hist(figsize=(10,6)); plt.tight_layout(); plt.savefig(MODEL.parent/'feature_distributions.png'); plt.close()
    return results
def predict(features):
    if not MODEL.exists(): raise RuntimeError('Train ML first: python manage.py train_models')
    with MODEL.open('rb') as stream: artifact=pickle.load(stream)
    frame=clean(pd.DataFrame([features])); frame[NUM]=frame[NUM].clip(upper=artifact['caps'],axis=1)
    return float(artifact['pipeline'].predict_proba(frame)[0,1])
