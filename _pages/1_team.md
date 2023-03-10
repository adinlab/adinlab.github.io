---
layout: page
permalink: /team/
title: team
description: 
nav: true
# nav_order: 3
---
<article>
<!-- <header class="post-header">
    <h1 class="post-title">Adaptive Intelligence Lab </h1>
</header> -->

{% if site.data.team.leaders %}
    <br><h2 id="principal-investigator">Principal Investigator</h2>
    <div class="row">
        <div class="projects column">
            {% assign sorted= site.data.team.leaders | sort: "name" %}
            {% for member in sorted %}
                {% include team/leader.html member=member %}
            {% endfor %}
        </div>
    </div>
{% endif %}


{% if site.data.team.postdoctorals %}
    <br><h2 id="postdoctoral-researchers">Postdoctoral Researchers</h2>
    <div class="row">
        {% assign sorted= site.data.team.postdoctorals | sort: "name" %}
        {% if site.data.team.postdoctorals.size > 2 %}
            {% for member in sorted %}
                <div class="col-sm-3 d-flex align-items-stretch">
                    {% include team/active_member.html member=member %}
                </div>
            {% endfor %}
        {% else %}
            <div class="project column">
            {% for member in sorted %}
                <div class="col-sm-12 d-flex align-items-stretch">
                    {% include team/active_member_horizontal.html member=member %}
                </div>
            {% endfor %}
            </div>
        {% endif %}
    </div>
{% endif %}


{% if site.data.team.phds %}
    <br><h2 id="phd-students">PhD Students</h2>
    <div class="row">
        {% assign sorted= site.data.team.phds | sort: "name" %}
        {% for member in sorted %}
            <div class="col-sm-3 d-flex align-items-stretch">
                {% include team/active_member.html member=member %}
            </div>
        {% endfor %}
    </div>
{% endif %}


{% if site.data.team.mscs %}
    <br><h2 id="msc-students">MSc Students</h2>
    <div class="row">
        {% assign sorted= site.data.team.mscs | sort: "name" %}
        {% for member in sorted %}
            <div class="col-sm-3 d-flex align-items-stretch">
                {% include team/active_member.html member=member %}
            </div>
        {% endfor %}
    </div>
{% endif %}

{% if site.data.team.bscs %}
    <br><h2 id="bsc-students">BSc Students</h2>
    <div class="row">
        {% assign sorted= site.data.team.bscs | sort: "name" %}
        {% for member in sorted %}
            <div class="col-sm-3 d-flex align-items-stretch">
                {% include team/active_member.html member=member %}
            </div>
        {% endfor %}
    </div>
{% endif %}


{% if site.data.team.alumnis %}
    <br><h2 id="alumni">Alumni</h2>
    <div class="projects column">
        {% assign sorted= site.data.team.alumnis | sort: "name" %}
        {% include team/alumni.html alumnis=sorted %}
    </div>
{% endif %}


</article>
