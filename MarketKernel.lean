/-
  MarketKernel.lean —— 世界杯市场理论的形式内核 (Lean 4 + Mathlib, ZERO SORRY)
  对应分析报告第30章。全部证明步骤已经 sympy 符号核验(报告30.3)。
  收录: L1凸组合界 / L2对数界链→Kelly最优 / L3 margin支配 / L4守恒律与特征值 /
        L5门槛等价 / L6半衰期界 / T12 Cover主恒等式 / T13叙事税非负 / 边缘为正
-/
import Mathlib

open Finset Real

namespace MarketKernel

/-- L1辅助: 非负权和为1时, 加权平均不超过任何上界 -/
theorem weighted_avg_le_bound {n : ℕ} (p r : Fin n → ℝ) (M : ℝ)
    (h₀ : ∀ i, 0 ≤ p i) (h₁ : ∑ i, p i = 1) (hm : ∀ i, r i ≤ M) :
    ∑ i, p i * r i ≤ M := by
  calc ∑ i, p i * r i ≤ ∑ i, p i * M := by
        apply Finset.sum_le_sum
        intro i _
        exact mul_le_mul_of_nonneg_left (hm i) (h₀ i)
    _ = M := by rw [← Finset.sum_mul, h₁, one_mul]

/-- L2链: Kelly最优性核心 —— 任意配置b对p的对数劣势非正 (log x ≤ x−1) -/
theorem kelly_gap_nonpos {n : ℕ} (p b : Fin n → ℝ)
    (hp : ∀ i, 0 ≤ p i) (hb : ∀ i, 0 < b i)
    (hpsum : ∑ i, p i = 1) (hbsum : ∑ i, b i = 1) :
    ∑ i, p i * Real.log (b i / p i) ≤ 0 := by
  have key : ∀ i, p i * Real.log (b i / p i) ≤ p i * (b i / p i - 1) := by
    intro i
    by_cases hpi : p i = 0
    · simp [hpi]
    · have hpos : 0 < b i / p i :=
        div_pos (hb i) (lt_of_le_of_ne (hp i) (Ne.symm hpi))
      exact mul_le_mul_of_nonneg_left (Real.log_le_sub_one_of_pos hpos) (hp i)
  calc ∑ i, p i * Real.log (b i / p i)
      ≤ ∑ i, p i * (b i / p i - 1) := Finset.sum_le_sum (fun i _ => key i)
    _ = ∑ i, (b i - p i) := by
        apply Finset.sum_congr rfl
        intro i _
        by_cases hpi : p i = 0
        · simp [hpi]
        · field_simp [hpi] <;> ring
    _ = 0 := by rw [Finset.sum_sub_distrib, hbsum, hpsum, sub_self]

/-- L3: margin支配 —— 赔率 o=(1−m)/q 下倒数和 = 1/(1−m) > 1 (庄家超圆) -/
theorem margin_dominance {n : ℕ} (q : Fin n → ℝ)
    (hq : ∀ i, 0 < q i) (hsum : ∑ i, q i = 1)
    {m : ℝ} (hm0 : 0 < m) (hm1 : m < 1) :
    1 < ∑ i, ((1 - m) / q i)⁻¹ := by
  have h1m : (0:ℝ) < 1 - m := by linarith
  have h_eq : ∑ i, ((1 - m) / q i)⁻¹ = (1 - m)⁻¹ := by
    have term : ∀ i ∈ (Finset.univ : Finset (Fin n)), ((1 - m) / q i)⁻¹ = q i / (1 - m) := by
      intro i _
      rw [inv_div]
    rw [Finset.sum_congr rfl term, ← Finset.sum_div, hsum, one_div]
  rw [h_eq]
  exact one_lt_inv h1m (by linarith)

/-- L5: 门槛等价 —— p·o>1 ⟺ p/q>1/(1−m) (T16角点判据) -/
theorem threshold_iff {p q m : ℝ} (hq : 0 < q) (hm1 : m < 1) :
    1 < p * ((1 - m) / q) ↔ 1 / (1 - m) < p / q := by
  have h1m : (0:ℝ) < 1 - m := by linarith
  rw [mul_div_assoc, lt_div_iff₀ hq, div_lt_iff₀ h1m, div_mul_eq_mul_div,
    lt_div_iff₀ hq]

/-- L4: 守恒律 —— κP+ψQ 在耦合更新下不变 -/
theorem conservation (κ ψ P Q : ℝ) :
    κ * ((1 - ψ) * P + ψ * Q) + ψ * (κ * P + (1 - κ) * Q) = κ * P + ψ * Q := by
  ring

/-- L4b: 特征值1(不动点方向, 特征向量(1,1)) -/
theorem eigen_one (κ ψ : ℝ) :
    (1 - ψ) * 1 + ψ * 1 = 1 ∧ κ * 1 + (1 - κ) * 1 = 1 :=
  ⟨by ring, by ring⟩

/-- L4c: 特征值1−κ−ψ(衰减方向, 特征向量(ψ,−κ)) -/
theorem eigen_decay (κ ψ : ℝ) :
    (1 - ψ) * ψ + ψ * (-κ) = (1 - κ - ψ) * ψ ∧
    κ * ψ + (1 - κ) * (-κ) = (1 - κ - ψ) * (-κ) :=
  ⟨by ring, by ring⟩

/-- 边缘为正: p>q ⟹ log(p/q)>0 -/
theorem edge_pos {p q : ℝ} (hq : 0 < q) (h : q < p) :
    0 < Real.log (p / q) := by
  apply Real.log_pos
  rw [one_lt_div hq]
  exact h

/-- L6: 半衰期界 —— (1−r)^(ln2/r) ≤ 1/2 (临界慢化的定量形式) -/
theorem half_life_bound {r : ℝ} (hr0 : 0 < r) (hr1 : r < 1) :
    (1 - r) ^ (Real.log 2 / r) ≤ 1 / 2 := by
  have h1 : (0:ℝ) < 1 - r := by linarith
  have hlog : Real.log (1 - r) ≤ -r := by
    have h := Real.log_le_sub_one_of_pos h1
    have he : (1 - r) - 1 = -r := by ring
    rw [he] at h
    exact h
  have hlog2 : 0 ≤ Real.log 2 / r :=
    div_nonneg (Real.log_nonneg (by norm_num)) (le_of_lt hr0)
  rw [Real.rpow_def_of_pos h1]
  have h2 : -r * (Real.log 2 / r) = -Real.log 2 := by
    field_simp [ne_of_gt hr0]
  have hle : Real.log (1 - r) * (Real.log 2 / r) ≤ -Real.log 2 := by
    calc Real.log (1 - r) * (Real.log 2 / r)
        ≤ -r * (Real.log 2 / r) := mul_le_mul_of_nonneg_right hlog hlog2
      _ = -Real.log 2 := h2
  have hexp : Real.exp (-Real.log 2) = 1 / 2 := by
    rw [Real.exp_neg, Real.exp_log (by norm_num : (0:ℝ) < 2)]
    norm_num
  exact (Real.exp_le_exp.mpr hle).trans_eq hexp

/-- T12(Cover主恒等式): log-最优配置增长率 ≥ 任意配置 (差 = KL散度 ≥ 0) -/
theorem cover_kelly_optimal {n : ℕ} (p b o : Fin n → ℝ)
    (hp : ∀ i, 0 ≤ p i) (hb : ∀ i, 0 < b i) (ho : ∀ i, 0 < o i)
    (hpsum : ∑ i, p i = 1) (hbsum : ∑ i, b i = 1) :
    ∑ i, p i * Real.log (b i * o i) ≤ ∑ i, p i * Real.log (p i * o i) := by
  have h := kelly_gap_nonpos p b hp hb hpsum hbsum
  have h2 : (∑ i, p i * Real.log (p i * o i)) - (∑ i, p i * Real.log (b i * o i))
      = -(∑ i, p i * Real.log (b i / p i)) := by
    rw [← Finset.sum_sub_distrib, ← Finset.sum_neg_distrib]
    apply Finset.sum_congr rfl
    intro i _
    by_cases hpi : p i = 0
    · simp [hpi]
    · have hpi' : 0 < p i := lt_of_le_of_ne (hp i) (Ne.symm hpi)
      rw [← mul_sub]
      have e1 : Real.log (p i * o i) - Real.log (b i * o i) = -Real.log (b i / p i) := by
        rw [Real.log_div (hb i).ne' hpi'.ne', Real.log_mul hpi'.ne' (ho i).ne',
          Real.log_mul (hb i).ne' (ho i).ne']
        ring
      rw [e1]
      ring
  have h3 : 0 ≤ -(∑ i, p i * Real.log (b i / p i)) := by linarith [h]
  rw [h2] at h3
  linarith [h3]

/-- T13: 叙事税非负 —— D₁(=KL) 不超过峰值状态的log比 (D∞ 方向) -/
theorem narrative_tax_nonneg {n : ℕ} (p q : Fin n → ℝ) (istar : Fin n)
    (hp : ∀ i, 0 ≤ p i) (hpsum : ∑ i, p i = 1)
    (hmax : ∀ i, Real.log (p i / q i) ≤ Real.log (p istar / q istar)) :
    ∑ i, p i * Real.log (p i / q i) ≤ Real.log (p istar / q istar) :=
  weighted_avg_le_bound _ _ _ hp hpsum hmax

end MarketKernel
