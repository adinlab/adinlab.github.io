---
layout: page
permalink: /publications/
title: Publications
description: Publications reversed chronological order.
years: [2025, 2024, 2023, 2022] # TODO update for new papers if necessary
nav: true
# nav_order: 1
---
<!-- _pages/publications.md -->
<div class="publications">

{%- for y in page.years %}
  <h2 class="year">{{y}}</h2>
  {% bibliography -f papers -q @*[year={{y}}]* %}
{% endfor %}

</div>
