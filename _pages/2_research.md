---
layout: page
title: Research
permalink: /research/
description: 
nav: true
# nav_order: 2
---

Our root node problems are:

* <span style="color:#e87382; font-weight:bold;">Epistemics (E):</span> Developing predictors of agent perceptions with reliable uncertainty estimates.
* <span style="color:#738ecb; font-weight:bold;">Synergetics (S):</span> Developing adaptation algorithms for agents with uncertain perceptions operating in open-world environments.
* <span style="color:#d4b83a; font-weight:bold;">Non-asymptotics (N):</span> Predicting lifelong agent performance via mathematical statements.

which synergize via the following research questions:

<div class="row justify-content-center">
    <div class="mt-3 mt-md-0" style="width: 81.25%; max-width: 100%; background-color: #ffffff; border-radius: 8px; padding: 1rem;">
        {% include figure.liquid loading="eager" path="assets/root-node-questions.svg" title="Root node questions" class="img-fluid" %}
    </div>
</div>

We reached the following key outcomes:

* **(S+N)** One can learn an isomorphism of the latent dynamics of a controlled Markov process from hitting time observations, which can be used to train foundation policies. See our [IEL algorithm](https://arxiv.org/abs/2605.06470).
* **(N)** Reconstructing reinforcement learning theory from measure-theoretic foundations explains why deep actor-critics work well. See our [MTRL framework](https://arxiv.org/abs/2605.05791).
* **(E+S+N)** Deriving intrinsic reward from well-calibrated uncertainties of the return distributions speeds up adaptation to non-stationary environments. See our [DAIF](https://icml.cc/virtual/2026/poster/61877), [EPPO](https://openreview.net/forum?id=KTfTwxsVNE), and [WSB](https://arxiv.org/abs/2307.03587) algorithms.
* **(E+S)** Evidential uncertainty quantification enhances learning capacity in on-policy continuous control, classification, and image generation. See our [EPPO](https://openreview.net/forum?id=KTfTwxsVNE), [ETP](https://openreview.net/forum?id=84NMXTHYe-), and [EdVAE](https://www.sciencedirect.com/science/article/pii/S0031320324005430) algorithms.
* **(E+S)** PAC-Bayes bounds on parametric return distributions can be used for directed exploration to discover sparse rewards. See our [PBAC](https://arxiv.org/abs/2402.03055) and [PAC4SAC](https://arxiv.org/abs/2301.12776) algorithms.
* **(E+S)** One can exploit the direction of Bellman errors to improve the performance of actor-critic algorithms. See our [USAC](https://arxiv.org/abs/2406.03890) and [AEA](https://arxiv.org/abs/2507.23501) algorithms.
