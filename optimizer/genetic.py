"""
遗传算法参数优化器
"""
import random
import numpy as np
from typing import Type, Dict, List, Any, Tuple, Callable
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine
from strategy.base import BaseStrategy


class GeneticOptimizer:
    """
    遗传算法优化器
    
    适合参数空间较大的情况，比网格搜索更高效
    """
    
    def __init__(self, symbol: str, start_date: str, end_date: str,
                 initial_capital: float = 100000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self._data = None
    
    def _load_data(self):
        if self._data is None:
            from data.fetcher import DataFetcher
            print(f"加载 {self.symbol} 数据...")
            self._data = DataFetcher.get_stock_daily(
                self.symbol, self.start_date, self.end_date
            )
            print(f"数据加载完成")
    
    def _evaluate(self, strategy_class: Type[BaseStrategy], 
                  params: Dict[str, Any], metric: str) -> float:
        """评估单个参数组合"""
        try:
            strategy = strategy_class(**params)
            
            engine = BacktestEngine(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_capital=self.initial_capital
            )
            engine.data = self._data.copy()
            engine.set_strategy(strategy)
            
            result = engine.run()
            
            return getattr(result, metric)
        except:
            return -999  # 失败返回极小值
    
    def _create_individual(self, param_ranges: Dict[str, Tuple]) -> Dict[str, Any]:
        """创建一个个体（随机参数组合）"""
        individual = {}
        for name, (min_val, max_val, step) in param_ranges.items():
            if isinstance(min_val, int):
                individual[name] = random.randrange(min_val, max_val + 1, step)
            else:
                steps = int((max_val - min_val) / step)
                individual[name] = min_val + random.randint(0, steps) * step
        return individual
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """交叉"""
        child = {}
        for key in parent1:
            child[key] = random.choice([parent1[key], parent2[key]])
        return child
    
    def _mutate(self, individual: Dict, param_ranges: Dict[str, Tuple], 
                mutation_rate: float) -> Dict:
        """变异"""
        mutated = individual.copy()
        for name, (min_val, max_val, step) in param_ranges.items():
            if random.random() < mutation_rate:
                if isinstance(min_val, int):
                    mutated[name] = random.randrange(min_val, max_val + 1, step)
                else:
                    steps = int((max_val - min_val) / step)
                    mutated[name] = min_val + random.randint(0, steps) * step
        return mutated
    
    def optimize(self, strategy_class: Type[BaseStrategy],
                 param_ranges: Dict[str, Tuple],
                 metric: str = "sharpe_ratio",
                 population_size: int = 20,
                 generations: int = 10,
                 mutation_rate: float = 0.1,
                 elite_ratio: float = 0.2) -> List[Tuple[Dict, float]]:
        """
        执行遗传算法优化
        
        Args:
            strategy_class: 策略类
            param_ranges: 参数范围，如 {"short_period": (5, 30, 1), "long_period": (10, 60, 5)}
                          格式为 (min, max, step)
            metric: 优化目标
            population_size: 种群大小
            generations: 迭代代数
            mutation_rate: 变异率
            elite_ratio: 精英比例
        
        Returns:
            最优参数列表 [(params, score), ...]
        """
        self._load_data()
        
        print(f"遗传算法优化: 种群={population_size}, 代数={generations}")
        
        # 初始化种群
        population = [self._create_individual(param_ranges) for _ in range(population_size)]
        
        best_results = []
        
        for gen in range(generations):
            # 评估适应度
            fitness = []
            for ind in population:
                score = self._evaluate(strategy_class, ind, metric)
                fitness.append((ind, score))
            
            # 按适应度排序
            fitness.sort(key=lambda x: x[1], reverse=True)
            
            # 记录本代最优
            best_ind, best_score = fitness[0]
            print(f"第 {gen + 1} 代: 最优 {metric}={best_score:.4f}, 参数={best_ind}")
            
            if gen == generations - 1:
                best_results = fitness[:5]
                break
            
            # 选择精英
            elite_count = max(2, int(population_size * elite_ratio))
            elites = [ind for ind, _ in fitness[:elite_count]]
            
            # 生成下一代
            new_population = elites.copy()
            
            while len(new_population) < population_size:
                # 锦标赛选择
                parent1 = random.choice(fitness[:elite_count * 2])[0]
                parent2 = random.choice(fitness[:elite_count * 2])[0]
                
                # 交叉
                child = self._crossover(parent1, parent2)
                
                # 变异
                child = self._mutate(child, param_ranges, mutation_rate)
                
                new_population.append(child)
            
            population = new_population
        
        return best_results
    
    def report(self, results: List[Tuple[Dict, float]]):
        """输出报告"""
        print("\n" + "=" * 60)
        print("遗传算法优化结果")
        print("=" * 60)
        
        for i, (params, score) in enumerate(results, 1):
            print(f"\n第 {i} 名: 得分={score:.4f}")
            for k, v in params.items():
                print(f"  {k}: {v}")
