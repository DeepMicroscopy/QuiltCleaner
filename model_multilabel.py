from torch.utils.data.dataset import Dataset
import pytorch_lightning as pl
import timm
import torch.nn as nn
import torch.optim as optim
import numpy as np
from PIL import Image
import torch
import os

class CustomDataset(Dataset):
    def __init__(self, data_dir, df, transform=None):
        self.data_dir = data_dir
        self.transform = transform
        self.df = df

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        img_name = self.df.Image[idx]
        img_name = os.path.join(self.data_dir, img_name.split('/')[-1])
        image = np.array(Image.open(img_name).convert('RGB'))
        
        labels = torch.Tensor([int(x) for x in self.df.loc[idx,['Persons/Photos','Desktop/Windows/SlideViewer','Text/Logo in Image','Arrow/Annotation','Image Perspective/Quality','Additional (On-Slide) Overview','Additional Control Elements','Multi-Panel Image']].to_list()])
        if self.transform:
            image = self.transform(image=image)['image']
        return image, labels

class CNN(pl.LightningModule):
    def __init__(self, num_classes):
        super(CNN, self).__init__()
        # Use ResNest50d model from timm as base
        self.model = timm.create_model('resnet50d', pretrained=True)
        num_features = self.model.fc.in_features  # get the number of in_features of the last Linear layer

        
        self.model.fc = nn.Identity()
        
        # define a separate head for each class
        self.class_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(num_features, 1024),
                nn.ReLU(),
                nn.Linear(1024, 1)
            ) for _ in range(num_classes)
        ])

        self.learning_rate = 1e-4
        
    def forward(self, x):
        x = self.model(x)
        outputs = [torch.sigmoid(head(x)) for head in self.class_heads]
        return torch.cat(outputs, dim=1)
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        preds = self.forward(x)
        loss = nn.BCELoss()(preds, y.float())
        self.log("train_loss", loss)
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        preds = self.forward(x)
        loss = nn.BCELoss()(preds, y.float())
        self.log("val_loss", loss)
        return loss
    
    def configure_optimizers(self):
        return optim.Adam(self.parameters(), lr=0.001)