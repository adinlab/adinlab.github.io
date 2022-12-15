---
layout: page
permalink: /vacancies/
title: vacancies
description: 
nav: true
# nav_order: 3
---

{% assign active_vacancies = site.vacancies.vacancies | where  "active": "True" %}
{% assign sorted = active_vacancies | sort:"deadline" %}

<div class="row">
  {%- for vacancy in sorted -%}
    {% include vacancy.html vacancy=vacancy %}
  {%- endfor %}

</div>