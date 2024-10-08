import torch
import torch.nn as nn
import xgboost as xgb

from loguru import logger

class SimpleImageRegressor(nn.Module):
    def __init__(self, embedding_size):
        super(SimpleImageRegressor, self).__init__()
        self.fc = nn.Linear(embedding_size, 1)  # 간단한 선형 회귀 모델

    def forward(self, x):
        return self.fc(x)

class SimpleDNN(nn.Module):
    def __init__(self, input_dim: int, layer_dims: list[int], embed_dim: int, dropout_rate: float=.5, type: str = 'count'):
        super(SimpleDNN, self).__init__()
        self.input_dim: int = input_dim
        self.layer_dims: list[int] = [embed_dim + input_dim] + layer_dims
        self.embed_dim: int = embed_dim
        self.dropout_rate: float = dropout_rate
        self.layers: nn.Module = self._layers()
        if type == 'count':
            self.embedding: nn.Module = CountMorganEmbedding(self.embed_dim)
        elif type == 'atom':
            self.embedding: nn.Module = CountMorganAtomEmbedding(self.embed_dim)

    def _init_weights(self):
        for child in self.children():
            if isinstance(child, nn.Sequential):
                for grand_child in child.children():
                    if isinstance(grand_child, nn.Linear):
                        torch.nn.init.kaiming_uniform_(grand_child.weight)
            else:
                torch.nn.init.xavier_normal_(child.weight)

    def _layers(self):
        layers = []
        for i in range(len(self.layer_dims) - 1):
            layers.append(nn.LayerNorm(self.layer_dims[i]))
            layers.append(nn.Linear(self.layer_dims[i], self.layer_dims[i+1]))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(self.dropout_rate))
        layers.append(nn.Linear(self.layer_dims[-1], 1)) # FC layer

        return nn.Sequential(*layers)
    
    # def forward(self, x, similarity):
    def forward(self, x, embeddings):
        embeddings = self._transform(embeddings)
        # logger.info(f"before embedding: {x.size()}")
        embeddings = self.embedding(embeddings)
        # logger.info(f"after embedding: {x.size()}")
        embeddings = embeddings.view(x.size(0), -1)
        x = torch.concat([x, embeddings], dim=-1)
        # logger.info(f"after concat: {x.size()}")
        return self.layers(x)
    
    def _transform(self, x):
        # logger.info(f"transform input: {x.size()}")
        batch_size, indice_size = x.size()
        indices = torch.arange(indice_size) + 1 # plus 1 for padding embedding
        mask = torch.zeros_like(x).int()
        mask[x != 0] = 1
        mask = mask.view(batch_size, -1)
        output = mask * indices.to(mask.device)
        return output

class CountMorganEmbedding(nn.Module):
    def __init__(self, embed_dim:int, bit_size:int = 13_279, radius_size:int = 4):
        super().__init__()
        self.embed_dim = embed_dim
        self.bit_size = bit_size
        self.radius_size = radius_size
        self.embedding = nn.Embedding(self.bit_size * self.radius_size + 1, self.embed_dim, padding_idx=0)

    def forward(self, x):
        '''
            input:
                size: (batch, bit_size * radius_size)
            output:
                size: (batch, self.embed_dim)
        '''
        return torch.mean(self.embedding(x), dim=1)
    
class CountMorganAtomEmbedding(nn.Module):
    def __init__(self, embed_dim: int, atom_count:int = 13_279 * 72):
        super().__init__()
        self.embed_dim = embed_dim
        self.atom_count = atom_count
        self.atom_embedding = nn.Embedding(self.atom_count + 1, self.embed_dim, padding_idx=0)

    def forward(self, x):
        return torch.mean(self.atom_embedding(x), dim=1)


class XGBoost:
    def __init__(self, cfg, device) -> None:
        self.cfg = cfg
        self.device = device
        self.model: xgb.XGBRegressor = \
            xgb.XGBRegressor(
                n_estimators=cfg.n_estimators,
                learning_rate=cfg.learning_rate,
                max_depth=cfg.max_depth,
                objective='reg:squarederror',
                device=self.device,
            )

    def fit(self, X, Y, verbose=True):
        self.model.fit(X, Y, eval_set=[(X, Y)], verbose=verbose)

    def predict(self, X):
        return self.model.predict(X)
    
    def save_model(self, filename: str):
        self.model.save_model(filename)

    def load_model(self, filename: str):
        self.model.load_model(filename)
