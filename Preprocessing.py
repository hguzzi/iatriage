# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rZw4-xrAPpxQHSKuADlvWTu_ufljzgmD

##DRIVE MOUNT
"""

from google.colab import drive
drive.mount('/content/drive/', force_remount=True)

import os
my_drive_path = '/content/drive/MyDrive/GNN Triage'
os.chdir(my_drive_path)

"""##READ CSV"""

import pandas as pd
patient_priority = pd.read_csv('patient_priority.csv')

patient_priority.head(10)

patient_priority.pop("Unnamed: 0")

patient_priority.head(10)

patient_priority.shape

"""##PREPROCESSING

####Duplicates
"""

duplicates = patient_priority.duplicated().sum()
print("I valori duplicati sono: " + str(duplicates))

"""####Drop NaN"""

display(patient_priority.isnull().sum())

#see density plot on the histogram
import matplotlib.pyplot as plt
import seaborn as sb
def hist(df):
 #df2=df.drop(columns = ['MRD No.'])
 names=list(df.columns)
 plt.figure(figsize=(35, 35))
 for column_index, column in enumerate(names):
   plt.subplot(5, 5, column_index + 1)
   sb.histplot(df[column], kde=True)

sb.histplot(patient_priority['smoking_status'], kde=True)

patient_priority = patient_priority.dropna()

patient_priority.shape

patient_priority.reset_index(inplace=True)
patient_priority.pop("index")

"""#### Target"""

print('I valori unici della feature target {} sono {}'.format('triage', (patient_priority['triage'].unique())))

import matplotlib.pyplot as plt
def plot_pie(df):
 a = df['triage'].value_counts()
 classe = a.index
 count = a.values
 explode = (0.05, 0.05, 0.05,0.05)
 mycolors = ["yellow", "green", "orange", "red"]
 piechart = a.plot.pie(labels = classe, explode = explode, fontsize = 12, autopct ='%1.1f%%', figsize = (7,7),shadow = True, colors = mycolors)

plot_pie(patient_priority)

"""####Categorical features and Label Encoder

"""

def list_cat(df):
  features = df.columns
  cat = list()
  for name in features:
    if df[name].dtypes==object:
      cat.append(name)
  return cat

def cat_feat(df):
  cat = list_cat(df)
  for name in cat:
    print('I valori unici della feature {} sono {}'.format(name, len(df[name].unique())))

cat_feat(patient_priority)

def value_feat(df):
  cat = list_cat(df)
  for name in cat:
    print('I valori unici della feature {} sono {}'.format(name, (df[name].unique())))

value_feat(patient_priority)

#see how many incorrect values
def incorrect_values(df,dtype,word):
 features = df.columns
 for name in features:
   if df[name].dtype==dtype:
    print((df[name]==word).value_counts())

incorrect_values(patient_priority, object , 'Unknown')

import numpy as np
patient_priority = patient_priority.replace('Unknown', np.nan)

patient_priority['smoking_status'].fillna(patient_priority['smoking_status'].mode()[0], inplace = True)

categorical = list_cat(patient_priority)
print(categorical)

#encoding of real categorical features
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
patient_priority['Residence_type'] = le.fit_transform(patient_priority['Residence_type'])
patient_priority['smoking_status'] = le.fit_transform(patient_priority['smoking_status'])
patient_priority['triage'] = le.fit_transform(patient_priority['triage'])

for c in categorical:
  print('I valori unici della feature {} sono {}'.format(c, (patient_priority[c].unique())))

plot_pie(patient_priority)

"""#### Info Dataset"""

patient_priority.describe()

patient_priority.groupby(['triage']).mean()

"""####SMOTE + ENN and Min Max Scaler"""

dataset = patient_priority

df_toscale = dataset.drop('triage', inplace = False, axis = 1)

y = dataset['triage'].values

X = dataset.drop('triage', inplace = False, axis = 1)

from imblearn.combine import SMOTEENN
from collections import Counter
counter = Counter(y)
print('Before', counter)

smenn= SMOTEENN()
X, y = smenn.fit_resample(X,y)
counter = Counter(y)
print('After', counter)

from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
X_topredict = scaler.fit_transform(X)
df_scaled = pd.DataFrame(X_topredict, columns=df_toscale.columns)

df_scaled

#Save data
df_scaled.to_csv('df_scaled.csv')
target = pd.DataFrame(y)
target.to_csv('target.csv')