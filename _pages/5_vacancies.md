---
layout: page
permalink: /vacancies/
title: vacancies
description: 
nav: true
# nav_order: 3
---

{%- assign sorted = site.data.vacancies.vacancies | sort:"deadline" -%}

<div class="row">
  {%- for vacancy in sorted -%}
    {% if vacancy.active == "True" %}
      {% include vacancy.html vacancy=vacancy %}
    {% endif %}
  {%- endfor %}

</div>