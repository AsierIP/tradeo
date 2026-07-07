# Daily Research Bucket Matrix

Task: T-DAILY-FOCUS-UNIVERSE-001
Decision: DAILY_RESEARCH_BUCKET_MATRIX_READY_FOR_BUCKET_ONLY_FUTURE_TESTS

This is a bucket-aware preregistration matrix only. It does not run a backtest,
approve a pattern, create a paper/live candidate, emit previews, or send orders.

## Contract

- Universe version: `daily_focus_universe_v2`.
- Timeframe: `1d` for every future test row.
- Every bucket-test row requires FDR plus WRC/SPA controls.
- Every bucket-test row requires bucket-level metrics.
- Global aggregates are summary-only and cannot approve a Daily pattern.
- ETF macro rows remain separate from stock buckets.

## Buckets

- `mega_large_cap`
- `large_cap_core`
- `liquid_mid_cap`
- `liquid_small_cap`
- `high_beta_growth`
- `defensive_quality`
- `sector_leaders`
- `etf_macro`

## Families

- Pullback in trend: W20, W50, W100 with forward 3/5/10/20 day horizons.
- Gap continuation/reversal daily: same-day close, next-day close, 3-day and 5-day follow-through.
- Volatility contraction breakout: contraction window, breakout confirmation, fakeout controls.
- Relative strength / sector leadership: stock vs SPY, stock vs sector ETF, sector ETF vs SPY.

## Machine Artifacts

- `daily_research_bucket_matrix.csv`
- `daily_research_bucket_matrix.json`

## Rows

| test_id | family | bucket | variant | exit_horizon | global_aggregate_allowed |
| --- | --- | --- | --- | --- | --- |
| DRBM_V2_PB_W20_3d_mega_large_cap | pullback_in_trend | mega_large_cap | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_mega_large_cap | pullback_in_trend | mega_large_cap | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_mega_large_cap | pullback_in_trend | mega_large_cap | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_mega_large_cap | pullback_in_trend | mega_large_cap | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_mega_large_cap | pullback_in_trend | mega_large_cap | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_mega_large_cap | pullback_in_trend | mega_large_cap | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_mega_large_cap | pullback_in_trend | mega_large_cap | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_mega_large_cap | pullback_in_trend | mega_large_cap | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_mega_large_cap | pullback_in_trend | mega_large_cap | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_mega_large_cap | pullback_in_trend | mega_large_cap | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_mega_large_cap | pullback_in_trend | mega_large_cap | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_mega_large_cap | pullback_in_trend | mega_large_cap | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_mega_large_cap | gap_continuation_reversal_daily | mega_large_cap | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_mega_large_cap | gap_continuation_reversal_daily | mega_large_cap | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_mega_large_cap | gap_continuation_reversal_daily | mega_large_cap | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_mega_large_cap | gap_continuation_reversal_daily | mega_large_cap | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_mega_large_cap | volatility_contraction_breakout | mega_large_cap | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_mega_large_cap | relative_strength_sector_leadership | mega_large_cap | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_mega_large_cap | relative_strength_sector_leadership | mega_large_cap | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_mega_large_cap | relative_strength_sector_leadership | mega_large_cap | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_large_cap_core | pullback_in_trend | large_cap_core | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_large_cap_core | pullback_in_trend | large_cap_core | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_large_cap_core | pullback_in_trend | large_cap_core | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_large_cap_core | pullback_in_trend | large_cap_core | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_large_cap_core | pullback_in_trend | large_cap_core | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_large_cap_core | pullback_in_trend | large_cap_core | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_large_cap_core | pullback_in_trend | large_cap_core | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_large_cap_core | pullback_in_trend | large_cap_core | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_large_cap_core | pullback_in_trend | large_cap_core | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_large_cap_core | pullback_in_trend | large_cap_core | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_large_cap_core | pullback_in_trend | large_cap_core | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_large_cap_core | pullback_in_trend | large_cap_core | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_large_cap_core | gap_continuation_reversal_daily | large_cap_core | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_large_cap_core | gap_continuation_reversal_daily | large_cap_core | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_large_cap_core | gap_continuation_reversal_daily | large_cap_core | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_large_cap_core | gap_continuation_reversal_daily | large_cap_core | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_large_cap_core | volatility_contraction_breakout | large_cap_core | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_large_cap_core | relative_strength_sector_leadership | large_cap_core | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_large_cap_core | relative_strength_sector_leadership | large_cap_core | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_large_cap_core | relative_strength_sector_leadership | large_cap_core | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_liquid_mid_cap | pullback_in_trend | liquid_mid_cap | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_liquid_mid_cap | gap_continuation_reversal_daily | liquid_mid_cap | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_liquid_mid_cap | gap_continuation_reversal_daily | liquid_mid_cap | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_liquid_mid_cap | gap_continuation_reversal_daily | liquid_mid_cap | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_liquid_mid_cap | gap_continuation_reversal_daily | liquid_mid_cap | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_liquid_mid_cap | volatility_contraction_breakout | liquid_mid_cap | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_liquid_mid_cap | relative_strength_sector_leadership | liquid_mid_cap | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_liquid_mid_cap | relative_strength_sector_leadership | liquid_mid_cap | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_liquid_mid_cap | relative_strength_sector_leadership | liquid_mid_cap | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_liquid_small_cap | pullback_in_trend | liquid_small_cap | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_liquid_small_cap | gap_continuation_reversal_daily | liquid_small_cap | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_liquid_small_cap | gap_continuation_reversal_daily | liquid_small_cap | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_liquid_small_cap | gap_continuation_reversal_daily | liquid_small_cap | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_liquid_small_cap | gap_continuation_reversal_daily | liquid_small_cap | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_liquid_small_cap | volatility_contraction_breakout | liquid_small_cap | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_liquid_small_cap | relative_strength_sector_leadership | liquid_small_cap | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_liquid_small_cap | relative_strength_sector_leadership | liquid_small_cap | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_liquid_small_cap | relative_strength_sector_leadership | liquid_small_cap | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_high_beta_growth | pullback_in_trend | high_beta_growth | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_high_beta_growth | pullback_in_trend | high_beta_growth | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_high_beta_growth | pullback_in_trend | high_beta_growth | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_high_beta_growth | pullback_in_trend | high_beta_growth | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_high_beta_growth | pullback_in_trend | high_beta_growth | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_high_beta_growth | pullback_in_trend | high_beta_growth | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_high_beta_growth | pullback_in_trend | high_beta_growth | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_high_beta_growth | pullback_in_trend | high_beta_growth | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_high_beta_growth | pullback_in_trend | high_beta_growth | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_high_beta_growth | pullback_in_trend | high_beta_growth | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_high_beta_growth | pullback_in_trend | high_beta_growth | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_high_beta_growth | pullback_in_trend | high_beta_growth | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_high_beta_growth | gap_continuation_reversal_daily | high_beta_growth | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_high_beta_growth | gap_continuation_reversal_daily | high_beta_growth | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_high_beta_growth | gap_continuation_reversal_daily | high_beta_growth | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_high_beta_growth | gap_continuation_reversal_daily | high_beta_growth | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_high_beta_growth | volatility_contraction_breakout | high_beta_growth | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_high_beta_growth | relative_strength_sector_leadership | high_beta_growth | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_high_beta_growth | relative_strength_sector_leadership | high_beta_growth | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_high_beta_growth | relative_strength_sector_leadership | high_beta_growth | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_defensive_quality | pullback_in_trend | defensive_quality | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_defensive_quality | pullback_in_trend | defensive_quality | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_defensive_quality | pullback_in_trend | defensive_quality | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_defensive_quality | pullback_in_trend | defensive_quality | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_defensive_quality | pullback_in_trend | defensive_quality | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_defensive_quality | pullback_in_trend | defensive_quality | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_defensive_quality | pullback_in_trend | defensive_quality | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_defensive_quality | pullback_in_trend | defensive_quality | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_defensive_quality | pullback_in_trend | defensive_quality | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_defensive_quality | pullback_in_trend | defensive_quality | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_defensive_quality | pullback_in_trend | defensive_quality | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_defensive_quality | pullback_in_trend | defensive_quality | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_defensive_quality | gap_continuation_reversal_daily | defensive_quality | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_defensive_quality | gap_continuation_reversal_daily | defensive_quality | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_defensive_quality | gap_continuation_reversal_daily | defensive_quality | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_defensive_quality | gap_continuation_reversal_daily | defensive_quality | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_defensive_quality | volatility_contraction_breakout | defensive_quality | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_defensive_quality | relative_strength_sector_leadership | defensive_quality | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_defensive_quality | relative_strength_sector_leadership | defensive_quality | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_defensive_quality | relative_strength_sector_leadership | defensive_quality | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_sector_leaders | pullback_in_trend | sector_leaders | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_sector_leaders | pullback_in_trend | sector_leaders | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_sector_leaders | pullback_in_trend | sector_leaders | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_sector_leaders | pullback_in_trend | sector_leaders | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_sector_leaders | pullback_in_trend | sector_leaders | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_sector_leaders | pullback_in_trend | sector_leaders | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_sector_leaders | pullback_in_trend | sector_leaders | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_sector_leaders | pullback_in_trend | sector_leaders | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_sector_leaders | pullback_in_trend | sector_leaders | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_sector_leaders | pullback_in_trend | sector_leaders | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_sector_leaders | pullback_in_trend | sector_leaders | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_sector_leaders | pullback_in_trend | sector_leaders | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_sector_leaders | gap_continuation_reversal_daily | sector_leaders | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_sector_leaders | gap_continuation_reversal_daily | sector_leaders | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_sector_leaders | gap_continuation_reversal_daily | sector_leaders | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_sector_leaders | gap_continuation_reversal_daily | sector_leaders | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_sector_leaders | volatility_contraction_breakout | sector_leaders | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_sector_leaders | relative_strength_sector_leadership | sector_leaders | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_sector_leaders | relative_strength_sector_leadership | sector_leaders | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_sector_leaders | relative_strength_sector_leadership | sector_leaders | sector_etf_vs_spy | 10d | false |
| DRBM_V2_PB_W20_3d_etf_macro | pullback_in_trend | etf_macro | W20 | 3d | false |
| DRBM_V2_PB_W20_5d_etf_macro | pullback_in_trend | etf_macro | W20 | 5d | false |
| DRBM_V2_PB_W20_10d_etf_macro | pullback_in_trend | etf_macro | W20 | 10d | false |
| DRBM_V2_PB_W20_20d_etf_macro | pullback_in_trend | etf_macro | W20 | 20d | false |
| DRBM_V2_PB_W50_3d_etf_macro | pullback_in_trend | etf_macro | W50 | 3d | false |
| DRBM_V2_PB_W50_5d_etf_macro | pullback_in_trend | etf_macro | W50 | 5d | false |
| DRBM_V2_PB_W50_10d_etf_macro | pullback_in_trend | etf_macro | W50 | 10d | false |
| DRBM_V2_PB_W50_20d_etf_macro | pullback_in_trend | etf_macro | W50 | 20d | false |
| DRBM_V2_PB_W100_3d_etf_macro | pullback_in_trend | etf_macro | W100 | 3d | false |
| DRBM_V2_PB_W100_5d_etf_macro | pullback_in_trend | etf_macro | W100 | 5d | false |
| DRBM_V2_PB_W100_10d_etf_macro | pullback_in_trend | etf_macro | W100 | 10d | false |
| DRBM_V2_PB_W100_20d_etf_macro | pullback_in_trend | etf_macro | W100 | 20d | false |
| DRBM_V2_GAP_same_day_close_etf_macro | gap_continuation_reversal_daily | etf_macro | same_day_close | same_day_close | false |
| DRBM_V2_GAP_next_day_close_etf_macro | gap_continuation_reversal_daily | etf_macro | next_day_close | next_day_close | false |
| DRBM_V2_GAP_3_day_follow_through_etf_macro | gap_continuation_reversal_daily | etf_macro | 3_day_follow_through | 3d | false |
| DRBM_V2_GAP_5_day_follow_through_etf_macro | gap_continuation_reversal_daily | etf_macro | 5_day_follow_through | 5d | false |
| DRBM_V2_VCB_etf_macro | volatility_contraction_breakout | etf_macro | contraction_window_breakout_confirmation_fakeout_controls | 5d | false |
| DRBM_V2_RS_stock_vs_spy_etf_macro | relative_strength_sector_leadership | etf_macro | stock_vs_spy | 10d | false |
| DRBM_V2_RS_stock_vs_sector_etf_etf_macro | relative_strength_sector_leadership | etf_macro | stock_vs_sector_etf | 10d | false |
| DRBM_V2_RS_sector_etf_vs_spy_etf_macro | relative_strength_sector_leadership | etf_macro | sector_etf_vs_spy | 10d | false |
| DRBM_V2_SUMMARY_ONLY | summary | all_buckets_summary_only | summary_only | summary_only | true |
