---
layout: page
permalink: /team/
title: Team
description: 
nav: true
# nav_order: 3
---
<article>
<!-- <header class="post-header">
    <h1 class="post-title">Adaptive Intelligence Lab </h1>
</header> -->

{% if site.data.team.faculty %}
    <br><h2 id="faculty">Faculty</h2>
    <div class="row">
        {% assign sorted= site.data.team.faculty | sort: "order" %}
        {% for member in sorted %}
            <div class="col-sm-4 d-flex align-items-stretch">
                {% include team/faculty.html member=member %}
            </div>
        {% endfor %}
    </div>
{% endif %}


{% if site.data.team.researchers %}
    <br><h2 id="research-fellows">Research Fellows</h2>
    <div class="row">
        {% assign sorted= site.data.team.researchers | sort: "name" %}
        {% for member in sorted %}
            <div class="col-sm-4 d-flex align-items-stretch">
                {% include team/active_member.html member=member %}
            </div>
        {% endfor %}
    </div>
{% endif %}


<!-- {% if site.data.team.mscs %}
    <br><h2 id="msc-students">MSc Students</h2>
    <div class="row">
        {% assign sorted= site.data.team.mscs | sort: "name" %}
        {% for member in sorted %}
            <div class="col-sm-3 d-flex align-items-stretch">
                {% include team/active_member.html member=member %}
            </div>
        {% endfor %}
    </div>
{% endif %} -->




{% if site.data.team.alumnis_msc %}
    <br><h2 id="alumni">Alumni</h2>
    <p> </p>
    <div class="card hoverable">
        <div class="row no-gutters">
            <div class="projects column">
                {% include team/alumni_phd.html alumnis=site.data.team.alumni_phd %}
                {% assign sorted= site.data.team.alumnis_msc %}
                {% include team/alumni_bsc.html alumnis=sorted %}
            </div>
        </div>
    </div>
{% endif %}


</article>
