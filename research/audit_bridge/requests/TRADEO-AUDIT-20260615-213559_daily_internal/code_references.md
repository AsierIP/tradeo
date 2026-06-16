# Code References

## PATTERN_000200

Pattern name: `DISCOVERED_SHORT_W50_C10_4142FAF4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000466

Pattern name: `DISCOVERED_SHORT_W50_C00_CE8AA7CF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000410

Pattern name: `DISCOVERED_SHORT_W50_C04_CD3D1332`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000617

Pattern name: `DISCOVERED_SHORT_W50_C00_989C652E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000103

Pattern name: `DISCOVERED_SHORT_W50_C10_CC719DB4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000349

Pattern name: `DISCOVERED_SHORT_W50_C00_DB64E1F9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000223

Pattern name: `DISCOVERED_LONG_W20_C02_6708F3E9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000694

Pattern name: `DISCOVERED_SHORT_W50_C09_1305EF64`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000258

Pattern name: `DISCOVERED_SHORT_W50_C04_DB295C4E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000237

Pattern name: `DISCOVERED_SHORT_W50_C06_3282E3E4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000490

Pattern name: `DISCOVERED_SHORT_W50_C03_38E81507`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000104

Pattern name: `DISCOVERED_SHORT_W50_C03_910C25FE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000238

Pattern name: `DISCOVERED_SHORT_W50_C00_58E580BC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000432

Pattern name: `DISCOVERED_LONG_W20_C03_49116A34`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000105

Pattern name: `DISCOVERED_SHORT_W50_C11_3DDBA7B3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000298

Pattern name: `DISCOVERED_SHORT_W50_C01_094783A3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000319

Pattern name: `DISCOVERED_LONG_W20_C01_62C81CD3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000068

Pattern name: `DISCOVERED_LONG_W50_C01_4C05BFF3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000069

Pattern name: `DISCOVERED_LONG_W50_C00_DB2FF044`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000618

Pattern name: `DISCOVERED_SHORT_W50_C09_2A26CD6D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000013

Pattern name: `DISCOVERED_SHORT_W50_C00_F47180E1`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000387

Pattern name: `DISCOVERED_SHORT_W50_C04_AE70270F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000070

Pattern name: `DISCOVERED_LONG_W20_C05_48C37C4A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000467

Pattern name: `DISCOVERED_SHORT_W50_C10_2C28691B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000259

Pattern name: `DISCOVERED_SHORT_W50_C08_8B47A583`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000468

Pattern name: `DISCOVERED_SHORT_W50_C08_705CA552`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000014

Pattern name: `DISCOVERED_SHORT_W50_C02_DDA81ECF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000058

Pattern name: `DISCOVERED_LONG_W20_C00_2123368A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000046

Pattern name: `DISCOVERED_SHORT_W20_C01_13BE9FFF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000619

Pattern name: `DISCOVERED_SHORT_W50_C08_D1B0940D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000560

Pattern name: `DISCOVERED_SHORT_W50_C02_18ED21F8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000514

Pattern name: `DISCOVERED_SHORT_W50_C02_425F8549`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000582

Pattern name: `DISCOVERED_SHORT_W50_C08_16CE35DA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000143

Pattern name: `DISCOVERED_SHORT_W50_C09_E6436663`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000537

Pattern name: `DISCOVERED_SHORT_W50_C03_6F238DAA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000080

Pattern name: `DISCOVERED_LONG_W20_C01_FAF17EEC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000561

Pattern name: `DISCOVERED_SHORT_W50_C10_33D735AC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000127

Pattern name: `DISCOVERED_SHORT_W50_C00_C9B4835A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000015

Pattern name: `DISCOVERED_SHORT_W50_C08_E0DAC825`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000035

Pattern name: `DISCOVERED_SHORT_W50_C05_09EBA0CA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000491

Pattern name: `DISCOVERED_SHORT_W50_C11_201AE277`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000144

Pattern name: `DISCOVERED_LONG_W50_C01_8C9CBF25`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000260

Pattern name: `DISCOVERED_SHORT_W50_C06_C5C763DB`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000515

Pattern name: `DISCOVERED_SHORT_W50_C07_20B54A1F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000282

Pattern name: `DISCOVERED_LONG_W20_C05_43AA830F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000201

Pattern name: `DISCOVERED_SHORT_W50_C02_B1AF15AF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000363

Pattern name: `DISCOVERED_SHORT_W50_C04_9A6C2079`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000388

Pattern name: `DISCOVERED_SHORT_W50_C08_CC1A6072`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000081

Pattern name: `DISCOVERED_LONG_W20_C00_4512D515`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000433

Pattern name: `DISCOVERED_LONG_W20_C01_4A2C6E6F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000283

Pattern name: `DISCOVERED_SHORT_W50_C02_8F29F884`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000538

Pattern name: `DISCOVERED_SHORT_W50_C02_134DBD4A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000744

Pattern name: `DISCOVERED_SHORT_W50_C09_CF98DF42`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000583

Pattern name: `DISCOVERED_SHORT_W50_C11_B3A70DDE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000492

Pattern name: `DISCOVERED_SHORT_W50_C01_85A05D85`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000106

Pattern name: `DISCOVERED_SHORT_W50_C02_10656C72`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000516

Pattern name: `DISCOVERED_SHORT_W50_C00_2087414A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000175

Pattern name: `DISCOVERED_LONG_W20_C02_FEF1E222`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000493

Pattern name: `DISCOVERED_SHORT_W50_C04_7F45363A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000299

Pattern name: `DISCOVERED_SHORT_W50_C00_CDDE5007`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000082

Pattern name: `DISCOVERED_LONG_W20_C05_5041888B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000311

Pattern name: `DISCOVERED_LONG_W20_C04_0A636D40`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000224

Pattern name: `DISCOVERED_SHORT_W50_C00_41D516BE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000672

Pattern name: `DISCOVERED_SHORT_W50_C06_E64C069E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000584

Pattern name: `DISCOVERED_SHORT_W50_C06_0D7D93C3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000176

Pattern name: `DISCOVERED_LONG_W20_C09_58EDFF7A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000364

Pattern name: `DISCOVERED_SHORT_W50_C05_BBCCAF14`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000411

Pattern name: `DISCOVERED_SHORT_W50_C02_AF94189C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000261

Pattern name: `DISCOVERED_SHORT_W50_C09_6412D8A7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000160

Pattern name: `DISCOVERED_LONG_W20_C09_E469ED13`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000284

Pattern name: `DISCOVERED_LONG_W20_C03_BEBBB87A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000202

Pattern name: `DISCOVERED_SHORT_W50_C08_5A9FE370`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000315

Pattern name: `DISCOVERED_LONG_W20_C03_D3B42B39`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000365

Pattern name: `DISCOVERED_SHORT_W50_C02_B25A79C7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000059

Pattern name: `DISCOVERED_LONG_W20_C11_484F3A29`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000389

Pattern name: `DISCOVERED_LONG_W50_C09_D2C613A0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000653

Pattern name: `DISCOVERED_SHORT_W50_C04_D626058A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000017

Pattern name: `DISCOVERED_SHORT_W50_C09_DF73462A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000350

Pattern name: `DISCOVERED_SHORT_W20_C09_E7AD1A5A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000620

Pattern name: `DISCOVERED_SHORT_W50_C04_9BE87280`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000539

Pattern name: `DISCOVERED_SHORT_W50_C07_49AA6FDA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000435

Pattern name: `DISCOVERED_LONG_W20_C04_FA9C1C2E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000203

Pattern name: `DISCOVERED_SHORT_W50_C05_EB6227A7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000412

Pattern name: `DISCOVERED_LONG_W50_C03_54AE94BD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000517

Pattern name: `DISCOVERED_LONG_W50_C11_18982D2D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000336

Pattern name: `DISCOVERED_SHORT_W50_C00_65D8E1D4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000128

Pattern name: `DISCOVERED_LONG_W20_C08_2A34E2D6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000225

Pattern name: `DISCOVERED_LONG_W20_C04_04EF2C14`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000351

Pattern name: `DISCOVERED_SHORT_W50_C01_98900E01`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000204

Pattern name: `DISCOVERED_SHORT_W50_C07_22087A4C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000182

Pattern name: `DISCOVERED_LONG_W50_C06_BDC79400`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000469

Pattern name: `DISCOVERED_SHORT_W50_C05_B3502794`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000366

Pattern name: `DISCOVERED_SHORT_W50_C06_D53F85BD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000107

Pattern name: `DISCOVERED_SHORT_W50_C00_5BED805B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000177

Pattern name: `DISCOVERED_SHORT_W20_C05_4A0EE5FC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000337

Pattern name: `DISCOVERED_LONG_W20_C11_50CF6AD3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000183

Pattern name: `DISCOVERED_SHORT_W50_C01_2F677116`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000285

Pattern name: `DISCOVERED_LONG_W20_C11_5DD631BF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000262

Pattern name: `DISCOVERED_SHORT_W50_C02_DA0B95F5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000060

Pattern name: `DISCOVERED_LONG_W20_C04_A58C27FA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000320

Pattern name: `DISCOVERED_LONG_W20_C03_A44DA73A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000331

Pattern name: `DISCOVERED_SHORT_W20_C02_DB7CF226`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000071

Pattern name: `DISCOVERED_SHORT_W50_C02_720DF47C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000061

Pattern name: `DISCOVERED_LONG_W20_C02_897C0469`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000286

Pattern name: `DISCOVERED_SHORT_W50_C03_F9594C79`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000390

Pattern name: `DISCOVERED_SHORT_W50_C03_20DF1FD0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000016

Pattern name: `DISCOVERED_SHORT_W50_C06_6C7C8BB7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000562

Pattern name: `DISCOVERED_SHORT_W50_C01_DA0F1419`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000470

Pattern name: `DISCOVERED_SHORT_W50_C06_7AE97930`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000494

Pattern name: `DISCOVERED_SHORT_W50_C10_58F162DA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000129

Pattern name: `DISCOVERED_SHORT_W50_C01_BF7BA9DD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000316

Pattern name: `DISCOVERED_LONG_W20_C02_F2E76BEA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000453

Pattern name: `DISCOVERED_LONG_W20_C02_A1FABD04`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000621

Pattern name: `DISCOVERED_SHORT_W50_C03_BD6A8746`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000622

Pattern name: `DISCOVERED_SHORT_W50_C10_1C444BC6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000047

Pattern name: `DISCOVERED_LONG_W20_C01_AF0AFDF9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000239

Pattern name: `DISCOVERED_SHORT_W50_C04_D85C37A7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000317

Pattern name: `DISCOVERED_LONG_W20_C01_3DACCBDC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000413

Pattern name: `DISCOVERED_LONG_W20_C03_27E7715B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000318

Pattern name: `DISCOVERED_SHORT_W20_C00_DC0278A5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000447

Pattern name: `DISCOVERED_LONG_W20_C00_13FD818C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000518

Pattern name: `DISCOVERED_SHORT_W50_C08_41718DDD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000205

Pattern name: `DISCOVERED_LONG_W20_C02_141038FE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000332

Pattern name: `DISCOVERED_SHORT_W20_C05_2A303029`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000263

Pattern name: `DISCOVERED_SHORT_W50_C05_43DD1FAF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000563

Pattern name: `DISCOVERED_SHORT_W50_C08_43336D3A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000414

Pattern name: `DISCOVERED_SHORT_W50_C00_4125C10D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000108

Pattern name: `DISCOVERED_SHORT_W50_C01_2AC53356`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000338

Pattern name: `DISCOVERED_SHORT_W20_C07_06677B6D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000145

Pattern name: `DISCOVERED_SHORT_W50_C04_C6BA6EE4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000184

Pattern name: `DISCOVERED_SHORT_W50_C02_841A1A33`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000339

Pattern name: `DISCOVERED_SHORT_W50_C01_977B0774`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000585

Pattern name: `DISCOVERED_SHORT_W50_C01_BCEDCC30`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000367

Pattern name: `DISCOVERED_SHORT_W20_C04_C12BF955`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000368

Pattern name: `DISCOVERED_SHORT_W50_C08_341C32D3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000300

Pattern name: `DISCOVERED_SHORT_W20_C02_E7115EE3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000415

Pattern name: `DISCOVERED_LONG_W20_C07_1DCBEBD1`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000240

Pattern name: `DISCOVERED_LONG_W20_C02_45E50362`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000178

Pattern name: `DISCOVERED_LONG_W20_C04_2C5F379B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000495

Pattern name: `DISCOVERED_SHORT_W50_C07_DB192AF6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000605

Pattern name: `DISCOVERED_LONG_W20_C02_2F394B3C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000206

Pattern name: `DISCOVERED_SHORT_W50_C06_65E830B2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000062

Pattern name: `DISCOVERED_LONG_W20_C07_44F85F04`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000564

Pattern name: `DISCOVERED_SHORT_W50_C04_1A25BC52`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000098

Pattern name: `DISCOVERED_SHORT_W20_C03_15300D35`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000416

Pattern name: `DISCOVERED_LONG_W50_C05_19A7F7DF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000586

Pattern name: `DISCOVERED_SHORT_W20_C00_53B25BBC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000471

Pattern name: `DISCOVERED_SHORT_W50_C04_D17AA402`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000161

Pattern name: `DISCOVERED_SHORT_W50_C00_C4C5E003`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000207

Pattern name: `DISCOVERED_LONG_W20_C08_97DB76B4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000391

Pattern name: `DISCOVERED_SHORT_W50_C01_3D5255B1`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000162

Pattern name: `DISCOVERED_SHORT_W50_C03_288A654B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000417

Pattern name: `DISCOVERED_LONG_W20_C05_3DB3B2A4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000472

Pattern name: `DISCOVERED_LONG_W50_C11_3C8C89A5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000185

Pattern name: `DISCOVERED_SHORT_W20_C06_46643241`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000226

Pattern name: `DISCOVERED_LONG_W20_C07_703C6FBF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000130

Pattern name: `DISCOVERED_SHORT_W20_C05_DF29BD47`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000623

Pattern name: `DISCOVERED_SHORT_W50_C02_841B5BDC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000448

Pattern name: `DISCOVERED_LONG_W20_C04_82EEDBB8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000001

Pattern name: `DISCOVERED_LONG_W20_C05_798BAA44`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000325

Pattern name: `DISCOVERED_SHORT_W20_C05_0945756A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000072

Pattern name: `DISCOVERED_LONG_W20_C08_47A1C968`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000048

Pattern name: `DISCOVERED_LONG_W20_C04_DBC9C574`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000086

Pattern name: `DISCOVERED_LONG_W20_C01_3A48D7EF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000163

Pattern name: `DISCOVERED_LONG_W20_C05_FE7034DB`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000099

Pattern name: `DISCOVERED_SHORT_W20_C05_5213F8C4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000519

Pattern name: `DISCOVERED_SHORT_W50_C05_B51ABFCE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000496

Pattern name: `DISCOVERED_LONG_W20_C08_3D2EAA0B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000208

Pattern name: `DISCOVERED_SHORT_W50_C03_09F8DF48`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000449

Pattern name: `DISCOVERED_LONG_W20_C03_3AF2DE66`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000109

Pattern name: `DISCOVERED_SHORT_W50_C05_B4921D5C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000287

Pattern name: `DISCOVERED_LONG_W20_C06_5C5A8809`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000018

Pattern name: `DISCOVERED_SHORT_W50_C03_46AF3A56`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000179

Pattern name: `DISCOVERED_SHORT_W20_C03_C13B75C6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000083

Pattern name: `DISCOVERED_SHORT_W20_C02_FFC30036`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000110

Pattern name: `DISCOVERED_LONG_W20_C04_3A82821D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000288

Pattern name: `DISCOVERED_SHORT_W50_C01_723A97BF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000264

Pattern name: `DISCOVERED_SHORT_W50_C03_37004D9B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000227

Pattern name: `DISCOVERED_SHORT_W20_C09_91747F8E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000418

Pattern name: `DISCOVERED_SHORT_W50_C09_7DA661D4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000419

Pattern name: `DISCOVERED_LONG_W50_C08_9CD8429E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000436

Pattern name: `DISCOVERED_LONG_W20_C05_C7E4258C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000312

Pattern name: `DISCOVERED_SHORT_W20_C02_0B3E4E99`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000392

Pattern name: `DISCOVERED_SHORT_W50_C11_C17D8008`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000228

Pattern name: `DISCOVERED_SHORT_W20_C10_D1578C4E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000002

Pattern name: `DISCOVERED_SHORT_W20_C03_6A9EDC74`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000111

Pattern name: `DISCOVERED_SHORT_W50_C06_9F72B423`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000454

Pattern name: `DISCOVERED_LONG_W20_C11_F45EFE28`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000473

Pattern name: `DISCOVERED_SHORT_W50_C02_667592D7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000073

Pattern name: `DISCOVERED_LONG_W20_C00_DAD80BD8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000474

Pattern name: `DISCOVERED_LONG_W50_C07_C5A16B67`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000393

Pattern name: `DISCOVERED_LONG_W20_C11_DB2257B2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000265

Pattern name: `DISCOVERED_LONG_W20_C10_52FDCBEA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000131

Pattern name: `DISCOVERED_SHORT_W20_C04_40AFCA01`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000520

Pattern name: `DISCOVERED_SHORT_W50_C01_36023B1E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000313

Pattern name: `DISCOVERED_SHORT_W20_C01_ABB1802F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000394

Pattern name: `DISCOVERED_SHORT_W50_C10_8BF524AA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000420

Pattern name: `DISCOVERED_LONG_W20_C01_28ADCDA7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000587

Pattern name: `DISCOVERED_SHORT_W50_C04_9F21E25A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000540

Pattern name: `DISCOVERED_SHORT_W50_C05_1EC26341`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000369

Pattern name: `DISCOVERED_SHORT_W50_C09_56A0F227`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000289

Pattern name: `DISCOVERED_LONG_W20_C00_D61D41F0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000321

Pattern name: `DISCOVERED_LONG_W20_C00_4DA5A8D6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000541

Pattern name: `DISCOVERED_SHORT_W50_C09_2C4C58C7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000322

Pattern name: `DISCOVERED_LONG_W20_C02_32892E5A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000421

Pattern name: `DISCOVERED_SHORT_W50_C06_95958917`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000437

Pattern name: `DISCOVERED_LONG_W20_C11_BB7CFA28`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000146

Pattern name: `DISCOVERED_SHORT_W50_C03_A8E55DE4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000370

Pattern name: `DISCOVERED_SHORT_W50_C07_1E48BA63`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000132

Pattern name: `DISCOVERED_LONG_W20_C01_CE81F26F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000112

Pattern name: `DISCOVERED_SHORT_W50_C07_CD0AE5F2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000542

Pattern name: `DISCOVERED_LONG_W20_C02_A69F6809`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000371

Pattern name: `DISCOVERED_SHORT_W50_C00_E21E3237`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000100

Pattern name: `DISCOVERED_LONG_W20_C00_F184347D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000074

Pattern name: `DISCOVERED_LONG_W20_C06_E6012259`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000019

Pattern name: `DISCOVERED_LONG_W20_C00_BB49F870`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000241

Pattern name: `DISCOVERED_SHORT_W20_C11_646FE24F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000521

Pattern name: `DISCOVERED_SHORT_W50_C03_656612E3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000422

Pattern name: `DISCOVERED_LONG_W20_C11_FEFA4E60`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000333

Pattern name: `DISCOVERED_LONG_W20_C00_149E7FFE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000041

Pattern name: `DISCOVERED_LONG_W20_C08_78662FE9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000455

Pattern name: `DISCOVERED_LONG_W20_C04_4D953324`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000028

Pattern name: `DISCOVERED_SHORT_W50_C04_68EE8AB8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000423

Pattern name: `DISCOVERED_LONG_W50_C07_BB514FEA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000164

Pattern name: `DISCOVERED_LONG_W20_C06_E8EC609E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000475

Pattern name: `DISCOVERED_SHORT_W50_C03_CE6B76D8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000020

Pattern name: `DISCOVERED_LONG_W20_C10_99CDC926`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000301

Pattern name: `DISCOVERED_SHORT_W20_C01_3BD0F138`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000323

Pattern name: `DISCOVERED_LONG_W20_C04_27EA1B8B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000372

Pattern name: `DISCOVERED_SHORT_W50_C01_DA2F6F88`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000302

Pattern name: `DISCOVERED_SHORT_W20_C04_C1B80584`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000543

Pattern name: `DISCOVERED_LONG_W20_C01_556D6DEA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000242

Pattern name: `DISCOVERED_SHORT_W50_C09_131BFAB3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000438

Pattern name: `DISCOVERED_LONG_W20_C08_8075773F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000522

Pattern name: `DISCOVERED_LONG_W20_C01_476D76DE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000075

Pattern name: `DISCOVERED_LONG_W20_C01_76EF41D9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000450

Pattern name: `DISCOVERED_SHORT_W20_C05_90D1E186`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000395

Pattern name: `DISCOVERED_SHORT_W50_C02_43E7BDEE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000352

Pattern name: `DISCOVERED_LONG_W20_C10_4F4E959B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000209

Pattern name: `DISCOVERED_SHORT_W50_C11_D5EC8E36`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000303

Pattern name: `DISCOVERED_LONG_W20_C06_84974698`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000523

Pattern name: `DISCOVERED_LONG_W20_C09_1414C751`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000340

Pattern name: `DISCOVERED_LONG_W20_C09_5926989F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000113

Pattern name: `DISCOVERED_SHORT_W50_C09_A28175F1`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000076

Pattern name: `DISCOVERED_SHORT_W20_C04_FD950649`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000326

Pattern name: `DISCOVERED_LONG_W20_C04_8D9B85AF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000334

Pattern name: `DISCOVERED_SHORT_W20_C01_BD8C58F0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000049

Pattern name: `DISCOVERED_LONG_W20_C08_0889C3CE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000565

Pattern name: `DISCOVERED_SHORT_W50_C11_B95F6AC2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000624

Pattern name: `DISCOVERED_SHORT_W50_C05_46C722DF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000165

Pattern name: `DISCOVERED_LONG_W50_C02_6CD412C4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000434

Pattern name: `DISCOVERED_LONG_W20_C02_C3006706`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000021

Pattern name: `DISCOVERED_LONG_W20_C06_6EF60B39`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000524

Pattern name: `DISCOVERED_LONG_W20_C07_943E3CAC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000077

Pattern name: `DISCOVERED_SHORT_W20_C11_7B817880`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000566

Pattern name: `DISCOVERED_LONG_W20_C09_AA9C308D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000456

Pattern name: `DISCOVERED_LONG_W20_C08_DE273848`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000114

Pattern name: `DISCOVERED_LONG_W20_C10_A4E0B752`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000625

Pattern name: `DISCOVERED_LONG_W20_C10_BDC054CE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000439

Pattern name: `DISCOVERED_LONG_W20_C00_E28F7705`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000266

Pattern name: `DISCOVERED_LONG_W20_C09_24D08DB0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000525

Pattern name: `DISCOVERED_LONG_W20_C03_FCB57F7A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000186

Pattern name: `DISCOVERED_SHORT_W50_C07_03B538D0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000526

Pattern name: `DISCOVERED_SHORT_W50_C06_6A2BA7D7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000396

Pattern name: `DISCOVERED_LONG_W20_C07_9A873206`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000476

Pattern name: `DISCOVERED_SHORT_W20_C10_436D77D8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000210

Pattern name: `DISCOVERED_SHORT_W50_C01_BEB4FEC6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000588

Pattern name: `DISCOVERED_LONG_W20_C08_30F41225`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000327

Pattern name: `DISCOVERED_SHORT_W20_C01_5E8937EE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000267

Pattern name: `DISCOVERED_LONG_W50_C10_8A6A2246`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000626

Pattern name: `DISCOVERED_SHORT_W20_C04_D5F9C680`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000457

Pattern name: `DISCOVERED_LONG_W20_C05_E11E2EB8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000606

Pattern name: `DISCOVERED_LONG_W20_C04_27615711`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000477

Pattern name: `DISCOVERED_LONG_W20_C00_2E0D5E95`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000147

Pattern name: `DISCOVERED_SHORT_W50_C00_F3C1511C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000567

Pattern name: `DISCOVERED_SHORT_W50_C05_C5E8623A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000627

Pattern name: `DISCOVERED_LONG_W20_C03_FACF5D3A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000115

Pattern name: `DISCOVERED_LONG_W20_C05_07F5B55F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000353

Pattern name: `DISCOVERED_LONG_W20_C00_52545769`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000003

Pattern name: `DISCOVERED_LONG_W20_C01_06E08FF8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000354

Pattern name: `DISCOVERED_LONG_W20_C02_8529407B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000527

Pattern name: `DISCOVERED_SHORT_W50_C04_2687AC02`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000087

Pattern name: `DISCOVERED_LONG_W20_C04_EF417066`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000497

Pattern name: `DISCOVERED_SHORT_W50_C06_64356745`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000589

Pattern name: `DISCOVERED_LONG_W20_C01_7A792C9A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000544

Pattern name: `DISCOVERED_SHORT_W20_C04_8DEB273D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000063

Pattern name: `DISCOVERED_LONG_W20_C03_D3869825`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000424

Pattern name: `DISCOVERED_LONG_W20_C09_010A9409`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000478

Pattern name: `DISCOVERED_SHORT_W20_C09_3597EC9B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000528

Pattern name: `DISCOVERED_LONG_W20_C04_9988DDB3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000148

Pattern name: `DISCOVERED_LONG_W20_C11_9FA17C7D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000022

Pattern name: `DISCOVERED_LONG_W50_C07_99947AB8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000498

Pattern name: `DISCOVERED_SHORT_W50_C02_2D3806E9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000590

Pattern name: `DISCOVERED_LONG_W20_C03_5C5E3D2B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000101

Pattern name: `DISCOVERED_SHORT_W20_C02_3E4FD186`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000050

Pattern name: `DISCOVERED_LONG_W20_C05_81F57EE8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000346

Pattern name: `DISCOVERED_SHORT_W20_C03_8A107C50`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000328

Pattern name: `DISCOVERED_SHORT_W20_C00_E15CA01E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000290

Pattern name: `DISCOVERED_LONG_W50_C00_62249A99`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000397

Pattern name: `DISCOVERED_LONG_W20_C04_C17D07C5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000398

Pattern name: `DISCOVERED_LONG_W20_C10_23AFD7D8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000291

Pattern name: `DISCOVERED_LONG_W20_C10_817F04F9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000268

Pattern name: `DISCOVERED_SHORT_W20_C08_55CFE785`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000329

Pattern name: `DISCOVERED_SHORT_W20_C03_5474CDAD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000425

Pattern name: `DISCOVERED_LONG_W20_C06_FAD48C17`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000078

Pattern name: `DISCOVERED_LONG_W20_C10_BF980C60`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000399

Pattern name: `DISCOVERED_SHORT_W20_C08_5A15403C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000088

Pattern name: `DISCOVERED_LONG_W20_C08_017D87FF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000211

Pattern name: `DISCOVERED_SHORT_W20_C00_EF9774FC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000479

Pattern name: `DISCOVERED_LONG_W20_C03_54495ACA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000545

Pattern name: `DISCOVERED_SHORT_W50_C11_F3DB174B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000269

Pattern name: `DISCOVERED_LONG_W20_C03_70E7C15F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000440

Pattern name: `DISCOVERED_SHORT_W20_C01_F0569AAD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000051

Pattern name: `DISCOVERED_SHORT_W20_C02_76FE4B00`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000355

Pattern name: `DISCOVERED_LONG_W20_C08_9656FD2F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000480

Pattern name: `DISCOVERED_LONG_W20_C04_74D8DE76`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000187

Pattern name: `DISCOVERED_LONG_W20_C00_7138F66D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000004

Pattern name: `DISCOVERED_LONG_W20_C07_72CBA230`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000529

Pattern name: `DISCOVERED_LONG_W20_C00_3F0D7815`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000270

Pattern name: `DISCOVERED_LONG_W20_C05_88D6B1E7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000356

Pattern name: `DISCOVERED_LONG_W20_C07_686F1D97`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000116

Pattern name: `DISCOVERED_LONG_W20_C02_C086EFC5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000499

Pattern name: `DISCOVERED_SHORT_W20_C06_2A2558CF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000023

Pattern name: `DISCOVERED_LONG_W20_C11_A8CF022A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000546

Pattern name: `DISCOVERED_SHORT_W50_C01_1813860C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000292

Pattern name: `DISCOVERED_LONG_W20_C08_F227A7E4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000607

Pattern name: `DISCOVERED_SHORT_W20_C03_D52A3250`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000481

Pattern name: `DISCOVERED_SHORT_W50_C09_C87858FE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000591

Pattern name: `DISCOVERED_SHORT_W50_C00_B70ED71B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000089

Pattern name: `DISCOVERED_LONG_W20_C09_4302CE0E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000530

Pattern name: `DISCOVERED_LONG_W20_C02_AF8992B9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000347

Pattern name: `DISCOVERED_LONG_W20_C01_CA96AABE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000006

Pattern name: `DISCOVERED_LONG_W20_C06_D227716A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000500

Pattern name: `DISCOVERED_SHORT_W20_C11_589EBFC2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000628

Pattern name: `DISCOVERED_LONG_W20_C05_DF9E4342`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000243

Pattern name: `DISCOVERED_SHORT_W50_C03_9603309C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000084

Pattern name: `DISCOVERED_LONG_W20_C04_1D3FCC38`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000304

Pattern name: `DISCOVERED_LONG_W20_C05_9F0214E6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000314

Pattern name: `DISCOVERED_LONG_W20_C00_0088E221`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000341

Pattern name: `DISCOVERED_SHORT_W20_C03_5D832DFE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000373

Pattern name: `DISCOVERED_SHORT_W50_C10_75E92215`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000451

Pattern name: `DISCOVERED_LONG_W20_C01_C665EAA5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000608

Pattern name: `DISCOVERED_LONG_W20_C07_604018DE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000629

Pattern name: `DISCOVERED_LONG_W50_C07_C5147EA3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000212

Pattern name: `DISCOVERED_LONG_W20_C11_88DE1FDF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000180

Pattern name: `DISCOVERED_SHORT_W20_C06_55A637E5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000609

Pattern name: `DISCOVERED_LONG_W20_C00_A5555B6F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000149

Pattern name: `DISCOVERED_SHORT_W20_C09_75AEA334`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000181

Pattern name: `DISCOVERED_LONG_W20_C11_EEEEADE3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000293

Pattern name: `DISCOVERED_LONG_W20_C07_188ED318`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000229

Pattern name: `DISCOVERED_SHORT_W20_C11_A71A4EC4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000117

Pattern name: `DISCOVERED_SHORT_W20_C01_7BDA6ED8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000568

Pattern name: `DISCOVERED_SHORT_W50_C00_5B392478`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000482

Pattern name: `DISCOVERED_SHORT_W50_C01_B0B33DA2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000400

Pattern name: `DISCOVERED_SHORT_W50_C07_4D54BCF9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000166

Pattern name: `DISCOVERED_LONG_W20_C11_DC23F717`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000531

Pattern name: `DISCOVERED_LONG_W20_C05_F37A7C6C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000745

Pattern name: `DISCOVERED_SHORT_W50_C04_2B11A874`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000271

Pattern name: `DISCOVERED_SHORT_W50_C00_BC6D70B8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000294

Pattern name: `DISCOVERED_LONG_W20_C09_677FF2E9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000167

Pattern name: `DISCOVERED_LONG_W20_C03_9CCDF4E3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000064

Pattern name: `DISCOVERED_LONG_W20_C01_0A98DC6F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000569

Pattern name: `DISCOVERED_LONG_W20_C04_B46F2FCA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000630

Pattern name: `DISCOVERED_LONG_W20_C00_F4977896`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000483

Pattern name: `DISCOVERED_LONG_W20_C11_65347EAC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000244

Pattern name: `DISCOVERED_LONG_W20_C08_8C6020C4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000441

Pattern name: `DISCOVERED_LONG_W20_C09_5BE19335`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000133

Pattern name: `DISCOVERED_LONG_W20_C10_66A25591`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000031

Pattern name: `DISCOVERED_SHORT_W20_C02_C983171A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000134

Pattern name: `DISCOVERED_SHORT_W20_C07_473940B0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000547

Pattern name: `DISCOVERED_LONG_W20_C03_D59B7984`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000592

Pattern name: `DISCOVERED_LONG_W20_C02_5E60C311`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000090

Pattern name: `DISCOVERED_SHORT_W20_C00_7C7F0CBB`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000230

Pattern name: `DISCOVERED_LONG_W20_C05_CC9CB09A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000548

Pattern name: `DISCOVERED_LONG_W20_C06_62A04CCC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000024

Pattern name: `DISCOVERED_LONG_W20_C04_53B26AF4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000118

Pattern name: `DISCOVERED_SHORT_W20_C08_1032567B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000458

Pattern name: `DISCOVERED_LONG_W20_C09_E4253DC2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000052

Pattern name: `DISCOVERED_LONG_W20_C11_979E9B0E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000401

Pattern name: `DISCOVERED_SHORT_W50_C06_8D313156`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000213

Pattern name: `DISCOVERED_LONG_W20_C06_65F79ACA`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000188

Pattern name: `DISCOVERED_LONG_W20_C05_87939540`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000593

Pattern name: `DISCOVERED_SHORT_W50_C10_CBD546DE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000631

Pattern name: `DISCOVERED_LONG_W20_C11_22658033`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000272

Pattern name: `DISCOVERED_LONG_W20_C02_24EC33FB`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000168

Pattern name: `DISCOVERED_LONG_W20_C10_4B7CA7A6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000594

Pattern name: `DISCOVERED_LONG_W20_C10_9929DB96`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000402

Pattern name: `DISCOVERED_LONG_W20_C03_DACB1736`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000245

Pattern name: `DISCOVERED_LONG_W20_C09_296935E5`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000065

Pattern name: `DISCOVERED_SHORT_W20_C10_2D473577`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000426

Pattern name: `DISCOVERED_LONG_W20_C02_60E9A7DF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000570

Pattern name: `DISCOVERED_SHORT_W50_C03_F31E1892`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000571

Pattern name: `DISCOVERED_LONG_W20_C00_33F614D3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000214

Pattern name: `DISCOVERED_SHORT_W50_C00_46C7029B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000374

Pattern name: `DISCOVERED_LONG_W20_C00_659CABD7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000273

Pattern name: `DISCOVERED_SHORT_W20_C07_78E7E2B9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000085

Pattern name: `DISCOVERED_SHORT_W20_C03_8970A473`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000375

Pattern name: `DISCOVERED_SHORT_W20_C06_34EFD49C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000150

Pattern name: `DISCOVERED_LONG_W20_C02_BE597437`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000305

Pattern name: `DISCOVERED_SHORT_W20_C08_EFCC4F8D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000010

Pattern name: `DISCOVERED_LONG_W20_C11_71DA78DD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000549

Pattern name: `DISCOVERED_LONG_W20_C00_2A3EEBA9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000007

Pattern name: `DISCOVERED_LONG_W20_C10_44E97F61`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000215

Pattern name: `DISCOVERED_LONG_W20_C01_01232DBE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000403

Pattern name: `DISCOVERED_SHORT_W20_C05_76056E6F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000151

Pattern name: `DISCOVERED_SHORT_W50_C05_1BE15810`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000135

Pattern name: `DISCOVERED_SHORT_W50_C02_E2ED68AE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000632

Pattern name: `DISCOVERED_LONG_W20_C01_29FAB2E0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000501

Pattern name: `DISCOVERED_LONG_W20_C03_335AF000`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000152

Pattern name: `DISCOVERED_SHORT_W20_C06_519C04A3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000404

Pattern name: `DISCOVERED_SHORT_W20_C00_F7540D2E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000376

Pattern name: `DISCOVERED_SHORT_W20_C07_A7D07551`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000377

Pattern name: `DISCOVERED_LONG_W20_C11_08DEA78E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000189

Pattern name: `DISCOVERED_SHORT_W50_C08_590995C6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000357

Pattern name: `DISCOVERED_SHORT_W20_C01_CA7C172B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000306

Pattern name: `DISCOVERED_SHORT_W20_C07_8CA032CE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000427

Pattern name: `DISCOVERED_SHORT_W20_C00_D5E7157D`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000532

Pattern name: `DISCOVERED_LONG_W20_C06_FDB0C003`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000025

Pattern name: `DISCOVERED_LONG_W20_C03_075A1E53`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000484

Pattern name: `DISCOVERED_LONG_W20_C01_711218B8`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000274

Pattern name: `DISCOVERED_SHORT_W50_C01_1D6ACFE4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000136

Pattern name: `DISCOVERED_SHORT_W20_C00_BF04AD3A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000246

Pattern name: `DISCOVERED_SHORT_W50_C02_4C4CFBB3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000091

Pattern name: `DISCOVERED_SHORT_W20_C07_6390EA15`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000572

Pattern name: `DISCOVERED_LONG_W20_C03_0070B1A3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000428

Pattern name: `DISCOVERED_LONG_W20_C04_3C9E6C67`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000550

Pattern name: `DISCOVERED_SHORT_W50_C06_B091F795`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000459

Pattern name: `DISCOVERED_SHORT_W20_C03_A346AF36`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000358

Pattern name: `DISCOVERED_SHORT_W20_C11_9DA804BC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000034

Pattern name: `DISCOVERED_LONG_W50_C11_5C9E4593`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000216

Pattern name: `DISCOVERED_LONG_W20_C10_BC6A527E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000092

Pattern name: `DISCOVERED_SHORT_W20_C11_094B2306`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000633

Pattern name: `DISCOVERED_SHORT_W20_C06_A632D672`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000485

Pattern name: `DISCOVERED_SHORT_W20_C08_9F6063A9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000217

Pattern name: `DISCOVERED_LONG_W20_C09_B18A8045`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000190

Pattern name: `DISCOVERED_LONG_W20_C01_22ABEFAF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000247

Pattern name: `DISCOVERED_LONG_W20_C05_DBAF031E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000405

Pattern name: `DISCOVERED_SHORT_W50_C05_860F8D8C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000030

Pattern name: `DISCOVERED_SHORT_W50_C01_42C2B407`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000307

Pattern name: `DISCOVERED_LONG_W20_C11_7D0683BC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000573

Pattern name: `DISCOVERED_LONG_W20_C08_08D6485C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000275

Pattern name: `DISCOVERED_LONG_W20_C06_7A57C575`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000486

Pattern name: `DISCOVERED_LONG_W20_C07_0C23BE10`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000634

Pattern name: `DISCOVERED_LONG_W20_C02_CFD064DF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000502

Pattern name: `DISCOVERED_SHORT_W20_C09_92CAE690`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000574

Pattern name: `DISCOVERED_SHORT_W20_C05_4224040B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000551

Pattern name: `DISCOVERED_LONG_W20_C08_5C360351`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000231

Pattern name: `DISCOVERED_LONG_W20_C03_1CD72ABD`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000654

Pattern name: `DISCOVERED_LONG_W20_C08_F56589B3`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000595

Pattern name: `DISCOVERED_LONG_W20_C11_816F3B99`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000575

Pattern name: `DISCOVERED_LONG_W50_C06_C5D456FB`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000153

Pattern name: `DISCOVERED_LONG_W20_C07_75FEAFBE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000093

Pattern name: `DISCOVERED_SHORT_W20_C06_EA20B4BF`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000576

Pattern name: `DISCOVERED_LONG_W20_C11_AAEE0E1C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000610

Pattern name: `DISCOVERED_SHORT_W20_C11_19E5133B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000552

Pattern name: `DISCOVERED_LONG_W50_C08_686E4005`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000248

Pattern name: `DISCOVERED_SHORT_W20_C04_EA57B3D6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000533

Pattern name: `DISCOVERED_SHORT_W20_C08_34E86410`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000191

Pattern name: `DISCOVERED_SHORT_W20_C08_E541DC33`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000192

Pattern name: `DISCOVERED_LONG_W20_C10_C36E1106`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000596

Pattern name: `DISCOVERED_SHORT_W20_C05_1FE2A639`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000378

Pattern name: `DISCOVERED_SHORT_W20_C08_E42F0101`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000406

Pattern name: `DISCOVERED_LONG_W20_C09_CAF6546E`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000119

Pattern name: `DISCOVERED_LONG_W20_C03_5723D149`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000027

Pattern name: `DISCOVERED_SHORT_W20_C01_326BBE79`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000553

Pattern name: `DISCOVERED_SHORT_W20_C10_3BCDD43C`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000249

Pattern name: `DISCOVERED_SHORT_W20_C01_C3012E66`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000503

Pattern name: `DISCOVERED_SHORT_W50_C09_BA0D5198`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000577

Pattern name: `DISCOVERED_LONG_W20_C07_281A38D6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000005

Pattern name: `DISCOVERED_LONG_W20_C09_069B7D53`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000597

Pattern name: `DISCOVERED_LONG_W20_C04_FC7A590A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000460

Pattern name: `DISCOVERED_LONG_W50_C00_F4D70A2A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000053

Pattern name: `DISCOVERED_SHORT_W20_C07_E4BD4F9F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000250

Pattern name: `DISCOVERED_LONG_W20_C06_3B514902`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000635

Pattern name: `DISCOVERED_LONG_W50_C11_7176D1B4`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000295

Pattern name: `DISCOVERED_LONG_W20_C04_CAE59E94`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000232

Pattern name: `DISCOVERED_LONG_W20_C08_0391BB7F`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000721

Pattern name: `DISCOVERED_SHORT_W50_C02_9D7D0D1B`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000554

Pattern name: `DISCOVERED_LONG_W20_C07_FA8E52A6`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000276

Pattern name: `DISCOVERED_LONG_W20_C01_A2B5CA7A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000218

Pattern name: `DISCOVERED_LONG_W20_C03_42ABEBEE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000555

Pattern name: `DISCOVERED_LONG_W20_C11_0B6E62A2`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000251

Pattern name: `DISCOVERED_SHORT_W20_C10_87064281`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000252

Pattern name: `DISCOVERED_SHORT_W50_C01_CBE84B68`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000379

Pattern name: `DISCOVERED_LONG_W20_C02_B89CD780`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000219

Pattern name: `DISCOVERED_LONG_W20_C04_70DFA8A1`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000253

Pattern name: `DISCOVERED_LONG_W50_C05_51557FE0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000611

Pattern name: `DISCOVERED_LONG_W20_C01_4348D299`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000636

Pattern name: `DISCOVERED_SHORT_W20_C09_2BA2AA49`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000036

Pattern name: `DISCOVERED_LONG_W20_C08_85949F07`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000029

Pattern name: `DISCOVERED_LONG_W20_C08_519EBA3A`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000556

Pattern name: `DISCOVERED_SHORT_W50_C00_B3448FDC`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000578

Pattern name: `DISCOVERED_SHORT_W20_C10_E32CD737`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000534

Pattern name: `DISCOVERED_SHORT_W20_C11_8CF28483`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000612

Pattern name: `DISCOVERED_LONG_W20_C09_520F21CE`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000598

Pattern name: `DISCOVERED_LONG_W50_C05_E97D37E9`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000277

Pattern name: `DISCOVERED_LONG_W50_C07_FF1EC9B7`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000487

Pattern name: `DISCOVERED_LONG_W20_C05_BECF1229`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000342

Pattern name: `DISCOVERED_LONG_W20_C10_379374B0`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.


## PATTERN_000380

Pattern name: `DISCOVERED_SHORT_W20_C01_DA35BF44`

Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.

