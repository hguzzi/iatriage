# -*- coding: utf-8 -*-
"""uniqueManhattan.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1salVwdBdbl1Zg2IVidU3C-9yxFEV8KZB
"""

# Commented out IPython magic to ensure Python compatibility.
from google.colab import drive
drive.mount('/content/drive/', force_remount=True)
import os
my_drive_path = '/content/drive/MyDrive/GNN Triage/New_thresholds'
os.chdir(my_drive_path)

import pickle
with open("/content/drive/MyDrive/GNN Triage/New_thresholds/y.pickle", "rb") as f:
    y = pickle.load(f)

import pandas as pd
import time

df_scaled= pd.read_csv('df_scaled.csv')
df_scaled.pop("Unnamed: 0")

!pip install torch_geometric
# Install PyTorch Geometric
import torch
!pip install -q torch-scatter -f https://data.pyg.org/whl/torch-{torch.__version__}.html
!pip install -q torch-sparse -f https://data.pyg.org/whl/torch-{torch.__version__}.html
!pip install -q git+https://github.com/pyg-team/pytorch_geometric.git

# Visualization
import networkx as nx
import matplotlib.pyplot as plt
plt.rcParams['figure.dpi'] = 100
plt.rcParams.update({'font.size': 20})
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import manhattan_distances
from sklearn.metrics.pairwise import pairwise_distances
import networkx as nx
import numpy as np
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()

def graph_by_man_dist(df, threshold):
    # Create a graph where each node represents an instance.
    G = nx.Graph()
    i = 0
    for c, r in df.iterrows():
      node = i
      i += 1
      features={key:value for key, value in r.items()}
      G.add_node(node, **features)
    m = manhattan_distances(df)
    scaler = MinMaxScaler()
    m_norm = scaler.fit_transform(m)
    n=len(df.index)
    # Add an edge if the distance is < t.
    for i in range(n):
        for j in range(i+1, n):
          matrix=m_norm[i][j]
          if matrix <= threshold:
            G.add_edge(i,j, weight=matrix)
    return G

def graph_torch(df, threshold, y):
  from torch_geometric.utils.convert import from_networkx
  from torch_geometric.data import Data
  from torch import Tensor
  from torch_geometric.transforms import BaseTransform
  import torch_geometric.transforms as T

  start = time.time()
  print("Start Creating Graph")
  print(start)
  G = graph_by_man_dist(df, threshold)
  print('end creation')
  print('Number of edges')
  print(len(list(G.edges())))
  print('Number of isolated nodes')
  print(len(list(nx.isolates(G))))

  pyg_graph = from_networkx(G,group_node_attrs=all)
  edge_index=pyg_graph.edge_index
  data = Data(x=pyg_graph.x, edge_index=edge_index,y=torch.tensor(y))

  split = T.RandomNodeSplit(num_val=0.1, num_test=0.2)
  data = split(data)

  return data


def accuracy(pred_y, y):
    return ((pred_y == y).sum() / len(y)).item()

@torch.no_grad()
def test(model, data):
    model.eval()
    out = model(data.x.to(device), data.edge_index.to(device))
    acc = accuracy(out.argmax(dim=1)[data.test_mask.to(device)], data.y[data.test_mask].to(device))
    return acc


def tloader(data):
  from torch_geometric.loader import NeighborLoader
  from torch_geometric.utils import to_networkx
  train_loader = NeighborLoader(
      data,
      num_neighbors=[10]*5,
      batch_size=3000,
      input_nodes=data.train_mask)
  return train_loader


from torch.nn import Dropout
from torch_geometric.nn import SAGEConv
import torch.nn.functional as F

class GraphSAGE(torch.nn.Module):
  def __init__(self, dim_in, dim_out):
    super().__init__()
    self.sage1 = SAGEConv(dim_in, 64, aggr ='max')
    self.sage2 = SAGEConv(64, 32, aggr ='max')
    self.sage3 = SAGEConv(32, 16, aggr ='mean')
    self.sage4 = SAGEConv(16, 8, aggr ='max')
    self.sage5 = SAGEConv(8, dim_out, aggr ='max')
    self.optimizer = torch.optim.Adam(self.parameters(),
                                      lr=0.01,weight_decay=5e-4)

  def forward(self, x, edge_index):
    h = self.sage1(x, edge_index).relu()
    #h = F.dropout(h, p=0.1, training=self.training)
    h = self.sage2(h, edge_index).relu()
    #h = F.dropout(h, p=0.1, training=self.training)
    h = self.sage3(h, edge_index).relu()
    #h = F.dropout(h, p=0.1, training=self.training)
    h = self.sage4(h, edge_index).relu()
    h = F.dropout(h, p=0.2, training=self.training)
    h = self.sage5(h, edge_index)
    return F.log_softmax(h, dim=1)

  def fit(self, data, epochs, train_loader):

    criterion = torch.nn.CrossEntropyLoss()
    optimizer = self.optimizer

    self.train()
    for epoch in range(epochs+1):
      total_loss = 0
      acc = 0
      val_loss = 0
      val_acc = 0

      # Train on batches
      for batch in train_loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        accs=[]
        val_accs=[]
        out = self(batch.x.to(device), batch.edge_index.to(device))
        loss = criterion(out[batch.train_mask.to(device)], batch.y[batch.train_mask].to(device))
        total_loss += loss
        acc += accuracy(out[batch.train_mask.to(device)].argmax(dim=1),
                        batch.y[batch.train_mask].to(device))

        loss.backward()
        optimizer.step()

        # Validation
        val_loss += criterion(out[batch.val_mask.to(device)], batch.y[batch.val_mask].to(device))
        val_acc += accuracy(out[batch.val_mask.to(device)].argmax(dim=1),
                            batch.y[batch.val_mask].to(device))


      # Print metrics every 100 epochs
      if(epoch % 100 == 0):
          print(f'Epoch {epoch:>3} | Train Loss: {total_loss/len(train_loader):.3f} '
                f'| Train Acc: {acc/len(train_loader)*100:>6.2f}% | Val Loss: '
                f'{val_loss/len(train_loader):.2f} | Val Acc: '
                f'{val_acc/len(train_loader)*100:.2f}%')


def visualize(h, color):
#     %matplotlib inline
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE
    z = TSNE(n_components=2).fit_transform(h.detach().cpu().numpy())

    plt.figure(figsize=(10,10))
    plt.xticks([])
    plt.yticks([])

    plt.scatter(z[:, 0], z[:, 1], s=70, c=color, cmap="Set2")
    plt.show()


def save_model(graphsage, name_model):
  #path
  model_save_path = name_model
  #torch.save
  torch.save(graphsage.state_dict(), model_save_path)

def main(name_model, df, threshold, y):
  data = graph_torch(df, threshold, y).to(device)
  train_loader = tloader(data)

  graphsage = GraphSAGE(16, 4).to(device)

  #before train
  graphsage.eval().cpu()
  data = data.cpu()
  out_before = graphsage(data.x, data.edge_index)

  #after train
  graphsage = graphsage.to(device)
  data = data.to(device)
  graphsage.fit(data, 300, train_loader)
  graphsage.eval().cpu()
  data = data.cpu()
  out_after = graphsage(data.x, data.edge_index).cpu()

  graphsage = graphsage.to(device)
  data = data.to(device)

  save_model(graphsage, name_model)

  return visualize(out_before, color=data.y.cpu()), print(f'\nGraphSAGE test accuracy: {test(graphsage, data)*100:.2f}%\n'), visualize(out_after, color=data.y.cpu())

