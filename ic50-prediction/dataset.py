import os, random

from rdkit import Chem
from rdkit.Chem import Draw, AllChem

import pandas as pd
import numpy as np
from collections import Counter

import torch
from torchvision import transforms
from torch.utils.data import Dataset

from loguru import logger


class DataPreprocess:
    def __init__(self, 
                 data_dir: str, 
                 train_name: str = 'train.csv',
                 test_name: str = 'test.csv'):
        self.data_dir = data_dir
        self.train_name = train_name
        self.test_name = test_name
        self._load_datas()
        self._preprocess()
    
    def _load_datas(self):
        logger.info("[Preprocess] start loading datas...")
        self.train_df = pd.read_csv(os.path.join(self.data_dir, self.train_name))
        self.test_df = pd.read_csv(os.path.join(self.data_dir, self.test_name))
        logger.info("[Preprocess] end loading datas...")

    def _preprocess(self):
        def img_of(smiles: str):
            return Draw.MolToImage(Chem.MolFromSmiles(smiles))
        
        logger.info("[Preprocess] start preprocess train data...")
        self.train_df['assay'] = self.train_df['Assay ChEMBL ID'].apply(lambda v: v[6:])
        self.train_df['document'] = self.train_df['Document ChEMBL ID'].apply(lambda v: v[6:])
        self.train_df['molecule'] = self.train_df['Molecule ChEMBL ID'].apply(lambda v: v[6:])
        self.train_df = self.train_df.drop(self.train_df.columns[self.train_df.nunique() == 1], axis=1)
        self.train_df['img'] = self.train_df['Smiles'].apply(lambda x: img_of(x))
        self.train_df = self.train_df.drop(['Standard Value', 'pChEMBL Value', 'Assay ChEMBL ID', 'Document ChEMBL ID', 'Molecule ChEMBL ID'], axis=1)
        
        logger.info("[Preprocess] start preprocess test data...")
        self.test_df['img'] = self.test_df['Smiles'].apply(lambda x: img_of(x))
        logger.info("[Preprocess] end preprocess datas...")

    def split(self, valid_ratio: float = .2):
        logger.info("[Preprocess] split train_df into train and valid...")
        indices: int = range(len(self.train_df))
        valid_indices = random.sample(indices, int(len(indices) * valid_ratio))
        train_indices = sorted(list(set(indices) - set(valid_indices)))

        train_df = self.train_df.iloc[train_indices]
        valid_df = self.train_df.iloc[valid_indices]
        
        assert len(train_df) + len(valid_df) == len(self.train_df), f"train valid split fail: {len(train_df)} , {len(valid_df)} / {len(self.train_df)}"

        return train_df, valid_df, self.test_df
    
    def k_fold_split(self, k_fold: int = 5):
        logger.info("[Preprocess] split info k-fold...")
        k_folded_datasets = dict()

        size = len(self.train_df) // k_fold
        for fold in range(k_fold):
            valid_start_idx = fold * size
            valid_end_idx = min(len(self.train_df), (fold + 1) * size)

            valid_df = self.train_df.iloc[valid_start_idx:valid_end_idx]
            train_df = self.train_df.drop(valid_df.index)
            k_folded_datasets[fold] = {
                'train_df': train_df,
                'valid_df': valid_df,
            }

        return k_folded_datasets, self.test_df
    
class SimpleDNNPreprocess(DataPreprocess):
    def __init__(self, 
                 data_dir: str, 
                 train_name: str = 'train.csv',
                 test_name: str = 'test.csv'):
        super().__init__(data_dir, train_name, test_name)
    
    def _preprocess(self):
        # def img_of(smiles: str):
        #     return np.array(Draw.MolToImage(Chem.MolFromSmiles(smiles))) / 255.
        
        # # SMILES 데이터를 분자 지문으로 변환
        # def smiles_to_fingerprint(smiles):
        #     mol = Chem.MolFromSmiles(smiles)
        #     if mol is not None:
        #         fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
        #         return np.array(fp)
        #     else:
        #         return np.zeros((2048,))

        # logger.info("[SimpleDNNPreprocess] start preprocess train data...")
        # self.train_df = self.train_df.drop(self.train_df.columns[self.train_df.nunique() == 1], axis=1)

        # logger.info("[SimpleDNNPreprocess] ID split...")
        # self.train_df['assay'] = self.train_df['Assay ChEMBL ID'].apply(lambda v: v[6:])
        # self.train_df['document'] = self.train_df['Document ChEMBL ID'].apply(lambda v: v[6:])
        # self.train_df['molecule'] = self.train_df['Molecule ChEMBL ID'].apply(lambda v: v[6:])

        # self.train_df['document'] = self.train_df['document'].astype(int)
        # self.train_df['molecule'] = self.train_df['molecule'].astype(int)
        # self.train_df['assay'] = self.train_df['assay'].astype(int)

        # logger.info("[SimpleDNNPreprocess] Image transform...")
        # self.train_df['img'] = self.train_df['Smiles'].apply(img_of)
        # logger.info("[SimpleDNNPreprocess] Image transform...")
        # logger.info("[SimpleDNNPreprocess] Fingerprint...")
        # self.train_df['fingerprint'] = self.train_df['Smiles'].apply(smiles_to_fingerprint)
        # self.train_df = self.train_df.drop(['Standard Value', 'pChEMBL Value', 'Assay ChEMBL ID', 'Document ChEMBL ID', 'Molecule ChEMBL ID'], axis=1)

        # logger.info("[SimpleDNNPreprocess] Concat image and fingerprint...")
        # self.train_df['X'] = self.train_df.apply(
        #     lambda row: # [row['document'], row['molecule'], row['assay']] + 
        #                 row['img'].flatten().tolist()
        #     , axis=1
        # )
        # self.train_df['X'] = self.train_df.apply(lambda row: np.concat([row['X'], row['fingerprint']]), axis=1)

        # self.input_size = self.train_df['X'][0].shape # for model input size

        # logger.info("[SimpleDNNPreprocess] start preprocess test data...")
        # logger.info("[SimpleDNNPreprocess] Image transform...")
        # self.test_df['img'] = self.test_df['Smiles'].apply(img_of)
        # logger.info("[SimpleDNNPreprocess] Fingerprint...")
        # self.test_df['fingerprint'] = self.test_df['Smiles'].apply(smiles_to_fingerprint)
        # logger.info("[SimpleDNNPreprocess] Concat image and fingerprint...")
        # self.test_df['X'] = self.test_df.apply(
        #     lambda row: # [row['document'], row['molecule'], row['assay']] + 
        #                 row['img'].flatten().tolist()
        #     , axis=1
        # )
        # self.test_df['X'] = self.test_df.apply(lambda row: np.concat([row['X'], row['fingerprint']]), axis=1)

        logger.info(f"[SimpleDNNPreprocess] Transform to Morgan Embedding...")
        def smiles_to_morgan(smiles):
            mol = Chem.MolFromSmiles(smiles)
            if mol is not None:
                additional_output = AllChem.AdditionalOutput()
                additional_output.CollectBitInfoMap()
                morgan_gen = AllChem.GetMorganGenerator()
                morgan_gen.GetSparseCountFingerprint(mol, additionalOutput=additional_output)
                info = additional_output.GetBitInfoMap()
                return info
            else:
                return np.zeros((13_279,))
        
        self.train_df['morgan_info'] = self.train_df['Smiles'].apply(smiles_to_morgan)
        self.test_df['morgan_info'] = self.test_df['Smiles'].apply(smiles_to_morgan)

        morgan_key_set = set() # aggregate total morgan key set from train and test data
        self.train_df['morgan_info'].apply(lambda info: morgan_key_set.update(info.keys()))
        self.test_df['morgan_info'].apply(lambda info: morgan_key_set.update(info.keys()))

        morgan_key = sorted(list(morgan_key_set))
        total_morgan_key2idx = {k:i for i, k in enumerate(morgan_key)} # morgan key to idx

        def morgan_info_to_embedding(info, key_count=13_279, radius_count=4):
            embedding = np.zeros((key_count, radius_count, )) # init embedding

            for key, radius_list in info.items(): # iterate over morgan_infos
                radius_count = dict(Counter([radius[-1] for radius in radius_list])) # count radius's emerge count
                for radius, count in radius_count.items():
                    embedding[total_morgan_key2idx[key], radius] = count

            return embedding
        
        self.train_df['morgan_embedding'] = self.train_df['morgan_info'].apply(morgan_info_to_embedding)
        self.test_df['morgan_embedding'] = self.test_df['morgan_info'].apply(morgan_info_to_embedding)

        logger.info("[SimpleDNNPreprocess] standardization...")
        def standardization(embedding):
            mean = np.mean(embedding.flatten())
            std = np.std(embedding.flatten())

            return embedding - mean / std
        
        self.train_df['morgan_embedding'] = self.train_df['morgan_embedding'].apply(standardization)
        self.test_df['morgan_embedding'] = self.train_df['morgan_embedding'].apply(standardization)
        logger.info("[SimpleDNNPreprocess] end preprocess datas...")


class IC50Dataset(Dataset):
    def __init__(self, data: pd.DataFrame, train: bool=True):
        self.data = data
        self.transform = transforms.Compose([
            transforms.Resize((300, 300)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self.train = train

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        item = self.data.iloc[index]
        return {
            'X': self.transform(item['img']).view(-1,).to(torch.float32),
            'pIC50': item['pIC50'].astype('float32'),
            'IC50': item['IC50_nM'].astype('float32'),
        } if self.train else {
            'X': self.transform(item['img']).view(-1,).to(torch.float32),
        }

class SimpleDNNDataset(Dataset):
    def __init__(self, data: pd.DataFrame, train: bool) -> None:
        super().__init__()
        self.data: pd.DataFrame = data
        self.train: bool = train

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, index):
        item = self.data.iloc[index]
        return {
            # 'X': item['X'].astype('float32'),
            # 'X': item['fingerprint'].astype('float32'),
            'X': item['morgan_embedding'].flatten().astype('float32'),
            'pIC50': item['pIC50'].astype('float32'),
            'IC50': item['IC50_nM'].astype('float32'),
        } if self.train else {
            # 'X': item['X'].astype('float32'),
            # 'X': item['fingerprint'].astype('float32'),
            'X': item['morgan_embedding'].flatten().astype('float32'),
        }
    