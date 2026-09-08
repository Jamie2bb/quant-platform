"""
深度学习模型 - 参考 Qlib 的神经网络模型
用于股票收益预测
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class DeepModelBase:
    """深度学习模型基类"""
    
    def __init__(self, name: str = "DeepModel"):
        self.name = name
        self.model = None
        self.is_fitted = False
        self.device = "cpu"
    
    def _check_torch(self):
        """检查 PyTorch 是否安装"""
        try:
            import torch
            return True
        except ImportError:
            print("请安装 PyTorch: pip install torch")
            print("或访问 https://pytorch.org 获取安装命令")
            return False


class LSTMModel(DeepModelBase):
    """
    LSTM 时序预测模型
    
    适合捕捉股价的时序依赖关系
    """
    
    def __init__(self, input_size: int = 20, hidden_size: int = 64, 
                 num_layers: int = 2, dropout: float = 0.1,
                 sequence_length: int = 20):
        super().__init__("LSTM")
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.sequence_length = sequence_length
        
    def _build_model(self):
        """构建 LSTM 模型"""
        if not self._check_torch():
            return None
        
        import torch
        import torch.nn as nn
        
        class LSTMNet(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=dropout if num_layers > 1 else 0
                )
                self.fc = nn.Linear(hidden_size, 1)
                self.dropout = nn.Dropout(dropout)
                
            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                last_out = lstm_out[:, -1, :]
                out = self.dropout(last_out)
                return self.fc(out)
        
        return LSTMNet(self.input_size, self.hidden_size, 
                       self.num_layers, self.dropout)
    
    def _prepare_sequences(self, X: np.ndarray, y: np.ndarray = None) -> Tuple:
        """准备序列数据"""
        sequences = []
        targets = []
        
        for i in range(len(X) - self.sequence_length):
            seq = X[i:i + self.sequence_length]
            sequences.append(seq)
            if y is not None:
                targets.append(y[i + self.sequence_length])
        
        sequences = np.array(sequences)
        if y is not None:
            targets = np.array(targets)
            return sequences, targets
        return sequences
    
    def fit(self, X: pd.DataFrame, y: pd.Series, 
            epochs: int = 100, batch_size: int = 32, lr: float = 0.001):
        """
        训练模型
        
        Args:
            X: 特征 DataFrame
            y: 目标变量
            epochs: 训练轮数
            batch_size: 批大小
            lr: 学习率
        """
        if not self._check_torch():
            return self
        
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        
        # 数据预处理
        X_arr = X.fillna(0).values.astype(np.float32)
        y_arr = y.fillna(0).values.astype(np.float32)
        
        # 标准化
        self.X_mean = X_arr.mean(axis=0)
        self.X_std = X_arr.std(axis=0) + 1e-8
        X_norm = (X_arr - self.X_mean) / self.X_std
        
        # 准备序列
        X_seq, y_seq = self._prepare_sequences(X_norm, y_arr)
        
        if len(X_seq) == 0:
            print("数据不足，无法训练")
            return self
        
        # 更新 input_size
        self.input_size = X_seq.shape[2]
        
        # 构建模型
        self.model = self._build_model()
        if self.model is None:
            return self
        
        # 转换为 Tensor
        X_tensor = torch.FloatTensor(X_seq)
        y_tensor = torch.FloatTensor(y_seq).unsqueeze(1)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 训练
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                output = self.model(batch_X)
                loss = criterion(output, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.6f}")
        
        self.is_fitted = True
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        if not self.is_fitted or self.model is None:
            return pd.Series(0, index=X.index)
        
        import torch
        
        X_arr = X.fillna(0).values.astype(np.float32)
        X_norm = (X_arr - self.X_mean) / self.X_std
        X_seq = self._prepare_sequences(X_norm)
        
        if len(X_seq) == 0:
            return pd.Series(0, index=X.index)
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_seq)
            pred = self.model(X_tensor).numpy().flatten()
        
        # 对齐索引
        result = pd.Series(0.0, index=X.index)
        result.iloc[self.sequence_length:self.sequence_length + len(pred)] = pred
        
        return result


class TransformerModel(DeepModelBase):
    """
    Transformer 时序预测模型
    
    使用自注意力机制捕捉复杂的时序模式
    """
    
    def __init__(self, input_size: int = 20, d_model: int = 64,
                 nhead: int = 4, num_layers: int = 2, dropout: float = 0.1,
                 sequence_length: int = 20):
        super().__init__("Transformer")
        self.input_size = input_size
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.dropout = dropout
        self.sequence_length = sequence_length
    
    def _build_model(self):
        """构建 Transformer 模型"""
        if not self._check_torch():
            return None
        
        import torch
        import torch.nn as nn
        
        class TransformerNet(nn.Module):
            def __init__(self, input_size, d_model, nhead, num_layers, dropout, seq_len):
                super().__init__()
                self.input_fc = nn.Linear(input_size, d_model)
                
                # 位置编码
                self.pos_encoding = nn.Parameter(torch.randn(1, seq_len, d_model) * 0.1)
                
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=nhead,
                    dim_feedforward=d_model * 4,
                    dropout=dropout,
                    batch_first=True
                )
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                
                self.output_fc = nn.Sequential(
                    nn.Linear(d_model, d_model // 2),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(d_model // 2, 1)
                )
            
            def forward(self, x):
                # x: (batch, seq_len, input_size)
                x = self.input_fc(x)  # (batch, seq_len, d_model)
                x = x + self.pos_encoding
                x = self.transformer(x)  # (batch, seq_len, d_model)
                x = x[:, -1, :]  # 取最后一个时间步
                return self.output_fc(x)
        
        return TransformerNet(self.input_size, self.d_model, self.nhead,
                              self.num_layers, self.dropout, self.sequence_length)
    
    def _prepare_sequences(self, X: np.ndarray, y: np.ndarray = None) -> Tuple:
        """准备序列数据"""
        sequences = []
        targets = []
        
        for i in range(len(X) - self.sequence_length):
            seq = X[i:i + self.sequence_length]
            sequences.append(seq)
            if y is not None:
                targets.append(y[i + self.sequence_length])
        
        sequences = np.array(sequences)
        if y is not None:
            targets = np.array(targets)
            return sequences, targets
        return sequences
    
    def fit(self, X: pd.DataFrame, y: pd.Series,
            epochs: int = 100, batch_size: int = 32, lr: float = 0.001):
        """训练模型"""
        if not self._check_torch():
            return self
        
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        
        # 数据预处理
        X_arr = X.fillna(0).values.astype(np.float32)
        y_arr = y.fillna(0).values.astype(np.float32)
        
        # 标准化
        self.X_mean = X_arr.mean(axis=0)
        self.X_std = X_arr.std(axis=0) + 1e-8
        X_norm = (X_arr - self.X_mean) / self.X_std
        
        # 准备序列
        X_seq, y_seq = self._prepare_sequences(X_norm, y_arr)
        
        if len(X_seq) == 0:
            print("数据不足，无法训练")
            return self
        
        # 更新 input_size
        self.input_size = X_seq.shape[2]
        
        # 构建模型
        self.model = self._build_model()
        if self.model is None:
            return self
        
        # 转换为 Tensor
        X_tensor = torch.FloatTensor(X_seq)
        y_tensor = torch.FloatTensor(y_seq).unsqueeze(1)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 训练
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                output = self.model(batch_X)
                loss = criterion(output, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.6f}")
        
        self.is_fitted = True
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        if not self.is_fitted or self.model is None:
            return pd.Series(0, index=X.index)
        
        import torch
        
        X_arr = X.fillna(0).values.astype(np.float32)
        X_norm = (X_arr - self.X_mean) / self.X_std
        X_seq = self._prepare_sequences(X_norm)
        
        if len(X_seq) == 0:
            return pd.Series(0, index=X.index)
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_seq)
            pred = self.model(X_tensor).numpy().flatten()
        
        # 对齐索引
        result = pd.Series(0.0, index=X.index)
        result.iloc[self.sequence_length:self.sequence_length + len(pred)] = pred
        
        return result


class GRUModel(DeepModelBase):
    """
    GRU 时序预测模型
    
    比 LSTM 参数更少，训练更快
    """
    
    def __init__(self, input_size: int = 20, hidden_size: int = 64,
                 num_layers: int = 2, dropout: float = 0.1,
                 sequence_length: int = 20):
        super().__init__("GRU")
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.sequence_length = sequence_length
    
    def _build_model(self):
        """构建 GRU 模型"""
        if not self._check_torch():
            return None
        
        import torch
        import torch.nn as nn
        
        class GRUNet(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.gru = nn.GRU(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=dropout if num_layers > 1 else 0
                )
                self.fc = nn.Linear(hidden_size, 1)
                self.dropout = nn.Dropout(dropout)
                
            def forward(self, x):
                gru_out, _ = self.gru(x)
                last_out = gru_out[:, -1, :]
                out = self.dropout(last_out)
                return self.fc(out)
        
        return GRUNet(self.input_size, self.hidden_size,
                      self.num_layers, self.dropout)
    
    def _prepare_sequences(self, X: np.ndarray, y: np.ndarray = None) -> Tuple:
        """准备序列数据"""
        sequences = []
        targets = []
        
        for i in range(len(X) - self.sequence_length):
            seq = X[i:i + self.sequence_length]
            sequences.append(seq)
            if y is not None:
                targets.append(y[i + self.sequence_length])
        
        sequences = np.array(sequences)
        if y is not None:
            targets = np.array(targets)
            return sequences, targets
        return sequences
    
    def fit(self, X: pd.DataFrame, y: pd.Series,
            epochs: int = 100, batch_size: int = 32, lr: float = 0.001):
        """训练模型"""
        if not self._check_torch():
            return self
        
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        
        X_arr = X.fillna(0).values.astype(np.float32)
        y_arr = y.fillna(0).values.astype(np.float32)
        
        self.X_mean = X_arr.mean(axis=0)
        self.X_std = X_arr.std(axis=0) + 1e-8
        X_norm = (X_arr - self.X_mean) / self.X_std
        
        X_seq, y_seq = self._prepare_sequences(X_norm, y_arr)
        
        if len(X_seq) == 0:
            return self
        
        self.input_size = X_seq.shape[2]
        self.model = self._build_model()
        if self.model is None:
            return self
        
        X_tensor = torch.FloatTensor(X_seq)
        y_tensor = torch.FloatTensor(y_seq).unsqueeze(1)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                output = self.model(batch_X)
                loss = criterion(output, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.6f}")
        
        self.is_fitted = True
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        if not self.is_fitted or self.model is None:
            return pd.Series(0, index=X.index)
        
        import torch
        
        X_arr = X.fillna(0).values.astype(np.float32)
        X_norm = (X_arr - self.X_mean) / self.X_std
        X_seq = self._prepare_sequences(X_norm)
        
        if len(X_seq) == 0:
            return pd.Series(0, index=X.index)
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_seq)
            pred = self.model(X_tensor).numpy().flatten()
        
        result = pd.Series(0.0, index=X.index)
        result.iloc[self.sequence_length:self.sequence_length + len(pred)] = pred
        
        return result
