import os
import coverage
import requests

def generate_badge(coverage_percentage):
    color = "red"
    if coverage_percentage >= 85:
        color = "brightgreen"
    elif coverage_percentage >= 75:
        color = "yellow"
    elif coverage_percentage >= 50:
        color = "orange"

    badge_url = f"https://img.shields.io/badge/coverage-{coverage_percentage}%25-{color}.svg"
    response = requests.get(badge_url)
    with open("coverage-badge.svg", "wb") as f:
        f.write(response.content)

if __name__ == "__main__":
    cov = coverage.Coverage()
    cov.load()
    coverage_percentage = round(cov.report())
    generate_badge(coverage_percentage)