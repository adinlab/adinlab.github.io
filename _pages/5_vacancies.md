---
layout: page
permalink: /vacancies/
title: Vacancies
description: 
nav: true
# nav_order: 3
---

{%- assign sorted = site.data.vacancies.vacancies | sort:"deadline" -%}
{%- assign now = "now" | date: '%s' -%}
<div class="row">
  {%- for vacancy in sorted -%}
    {% if vacancy.active == "True" %}
      {%- assign deadline = vacancy.deadline | date: '%s' -%}
      {% if now  < deadline %}
        {% include vacancy.html vacancy=vacancy %}    
      {% endif %}
    {% endif %}
  {%- endfor %}

</div>