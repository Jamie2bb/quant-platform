"""
机器学习模型模块 - 参考 Qlib Model
用于因子选股和收益预测
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')


class BaseMLModel(ABC):
    """机器学习模型基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names: List[str] = []
    
    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series):
        """训练模型"""
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        pass
    
    def preprocess(self, X: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """数据预处理"""
        # 处理缺失值
        X_clean = X.fillna(X.mean())
        X_clean = X_clean.replace([np.inf, -np.inf], 0)
        
        # 标准化
        if fit:
            self.feature_names = X.columns.tolist()
            return self.scaler.fit_transform(X_clean)
        else:
            return self.scaler.transform(X_clean)
    
    def get_feature_importance(self) -> pd.Series:
        """获取特征重要性"""
        return pd.Series()


class LinearModel(BaseMLModel):
    """线性模型: 岭回归"""
    
    def __init__(self, alpha: float = 1.0):
        super().__init__("LinearModel")
        self.alpha = alpha
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        from sklearn.linear_model import Ridge
        
        X_scaled = self.preprocess(X, fit=True)
        y_clean = y.fillna(0)
        
        self.model = Ridge(alpha=self.alpha)
        self.model.fit(X_scaled, y_clean)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        X_scaled = self.preprocess(X, fit=False)
        pred = self.model.predict(X_scaled)
        return pd.Series(pred, index=X.index)
    
    def get_feature_importance(self) -> pd.Series:
        if not self.is_fitted:
            return pd.Series()
        return pd.Series(
            np.abs(self.model.coef_),
            index=self.feature_names
        ).sort_values(ascending=False)


class LightGBMModel(BaseMLModel):
    """LightGBM 模型"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 5, 
                 learning_rate: float = 0.1):
        super().__init__("LightGBM")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            import lightgbm as lgb
        except ImportError:
            print("请安装 lightgbm: pip install lightgbm")
            return self
        
        X_scaled = self.preprocess(X, fit=True)
        y_clean = y.fillna(0)
        
        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            verbose=-1
        )
        self.model.fit(X_scaled, y_clean)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        X_scaled = self.preprocess(X, fit=False)
        pred = self.model.predict(X_scaled)
        return pd.Series(pred, index=X.index)
    
    def get_feature_importance(self) -> pd.Series:
        if not self.is_fitted or self.model is None:
            return pd.Series()
        return pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)


class XGBoostModel(BaseMLModel):
    """XGBoost 模型"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 5,
                 learning_rate: float = 0.1):
        super().__init__("XGBoost")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        try:
            import xgboost as xgb
        except ImportError:
            print("请安装 xgboost: pip install xgboost")
            return self
        
        X_scaled = self.preprocess(X, fit=True)
        y_clean = y.fillna(0)
        
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            verbosity=0
        )
        self.model.fit(X_scaled, y_clean)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        X_scaled = self.preprocess(X, fit=False)
        pred = self.model.predict(X_scaled)
        return pd.Series(pred, index=X.index)
    
    def get_feature_importance(self) -> pd.Series:
        if not self.is_fitted or self.model is None:
            return pd.Series()
        return pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)


class RandomForestModel(BaseMLModel):
    """随机森林模型"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 10):
        super().__init__("RandomForest")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        from sklearn.ensemble import RandomForestRegressor
        
        X_scaled = self.preprocess(X, fit=True)
        y_clean = y.fillna(0)
        
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            n_jobs=-1,
            random_state=42
        )
        self.model.fit(X_scaled, y_clean)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        X_scaled = self.preprocess(X, fit=False)
        pred = self.model.predict(X_scaled)
        return pd.Series(pred, index=X.index)
    
    def get_feature_importance(self) -> pd.Series:
        if not self.is_fitted:
            return pd.Series()
        return pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)


class EnsembleModel(BaseMLModel):
    """
    集成模型
    
    组合多个模型的预测结果
    """
    
    def __init__(self, models: List[BaseMLModel] = None, weights: List[float] = None):
        super().__init__("Ensemble")
        
        if models is None:
            # 默认使用线性模型 + 随机森林
            self.models = [
                LinearModel(alpha=1.0),
                RandomForestModel(n_estimators=50, max_depth=5)
            ]
        else:
            self.models = models
        
        if weights is None:
            self.weights = [1.0 / len(self.models)] * len(self.models)
        else:
            self.weights = weights
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.feature_names = X.columns.tolist()
        
        for model in self.models:
            model.fit(X, y)
        
        self.is_fitted = True
        return self
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        predictions = []
        for model, weight in zip(self.models, self.weights):
            pred = model.predict(X)
            predictions.append(pred * weight)
        
        return sum(predictions)
    
    def get_feature_importance(self) -> pd.Series:
        """取各模型特征重要性的加权平均"""
        if not self.is_fitted:
            return pd.Series()
        
        importance = pd.Series(0.0, index=self.feature_names)
        
        for model, weight in zip(self.models, self.weights):
            model_importance = model.get_feature_importance()
            if len(model_importance) > 0:
                importance = importance.add(model_importance * weight, fill_value=0)
        
        return importance.sort_values(ascending=False)


class ModelTrainer:
    """
    模型训练器
    
    提供时序交叉验证、模型评估等功能
    """
    
    def __init__(self, model: BaseMLModel):
        self.model = model
        self.cv_results: List[dict] = []
    
    def time_series_cv(self, X: pd.DataFrame, y: pd.Series, 
                       n_splits: int = 5) -> dict:
        """
        时序交叉验证
        
        Returns:
            dict: 包含各折的评估指标
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        metrics = {
            "ic": [],  # Information Coefficient
            "rankic": [],  # Rank IC
            "mse": [],
        }
        
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # 训练
            self.model.fit(X_train, y_train)
            
            # 预测
            y_pred = self.model.predict(X_test)
            
            # 计算指标
            ic = np.corrcoef(y_test.fillna(0), y_pred.fillna(0))[0, 1]
            rankic = y_test.rank().corr(y_pred.rank())
            mse = ((y_test - y_pred) ** 2).mean()
            
            metrics["ic"].append(ic if not np.isnan(ic) else 0)
            metrics["rankic"].append(rankic if not np.isnan(rankic) else 0)
            metrics["mse"].append(mse)
        
        # 汇总结果
        results = {
            "ic_mean": np.mean(metrics["ic"]),
            "ic_std": np.std(metrics["ic"]),
            "rankic_mean": np.mean(metrics["rankic"]),
            "rankic_std": np.std(metrics["rankic"]),
            "mse_mean": np.mean(metrics["mse"]),
            "mse_std": np.std(metrics["mse"]),
        }
        
        self.cv_results.append(results)
        return results
    
    def train_and_evaluate(self, X_train: pd.DataFrame, y_train: pd.Series,
                           X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """训练并评估"""
        # 训练
        self.model.fit(X_train, y_train)
        
        # 预测
        y_pred = self.model.predict(X_test)
        
        # 评估
        ic = np.corrcoef(y_test.fillna(0), y_pred.fillna(0))[0, 1]
        rankic = y_test.rank().corr(y_pred.rank())
        mse = ((y_test - y_pred) ** 2).mean()
        
        return {
            "ic": ic if not np.isnan(ic) else 0,
            "rankic": rankic if not np.isnan(rankic) else 0,
            "mse": mse,
            "feature_importance": self.model.get_feature_importance()
        }


class FactorSelector:
    """
    因子选择器
    
    基于模型选择最有效的因子
    """
    
    def __init__(self, top_k: int = 10):
        self.top_k = top_k
        self.selected_factors: List[str] = []
        self.factor_scores: pd.Series = pd.Series()
    
    def select_by_ic(self, factors: pd.DataFrame, returns: pd.Series) -> List[str]:
        """
        根据 IC 选择因子
        
        Args:
            factors: 因子数据框，每列一个因子
            returns: 下期收益率
        
        Returns:
            选中的因子名称列表
        """
        ic_values = {}
        
        for col in factors.columns:
            factor = factors[col]
            # 计算 IC (因子值与下期收益的相关系数)
            valid_mask = ~(factor.isna() | returns.isna())
            if valid_mask.sum() > 30:
                ic = factor[valid_mask].corr(returns[valid_mask])
                ic_values[col] = abs(ic) if not np.isnan(ic) else 0
        
        self.factor_scores = pd.Series(ic_values).sort_values(ascending=False)
        self.selected_factors = self.factor_scores.head(self.top_k).index.tolist()
        
        return self.selected_factors
    
    def select_by_model(self, factors: pd.DataFrame, returns: pd.Series,
                        model: BaseMLModel = None) -> List[str]:
        """
        根据模型特征重要性选择因子
        """
        if model is None:
            model = RandomForestModel(n_estimators=50, max_depth=5)
        
        # 训练模型
        model.fit(factors, returns)
        
        # 获取特征重要性
        self.factor_scores = model.get_feature_importance()
        self.selected_factors = self.factor_scores.head(self.top_k).index.tolist()
        
        return self.selected_factors
    
    def get_report(self) -> str:
        """获取因子选择报告"""
        lines = ["=" * 50, "因子选择报告", "=" * 50, ""]
        lines.append(f"选中因子数: {len(self.selected_factors)}")
        lines.append("\n因子得分排名:")
        
        for i, (factor, score) in enumerate(self.factor_scores.head(self.top_k).items(), 1):
            lines.append(f"  {i}. {factor}: {score:.4f}")
        
        return "\n".join(lines)
