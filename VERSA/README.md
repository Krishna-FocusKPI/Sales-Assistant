<div align="center">
<img src="assets/banner.png" height='250'>
<h1 align="center"> VERSA <br/> Virtual Employee Response & Service Assistant</h1>


![](https://img.shields.io/badge/build-passing-green.svg)
![](https://img.shields.io/badge/language-python-green.svg)
![](https://img.shields.io/badge/version-1.0-blue.svg)
![](https://img.shields.io/badge/python-%203.11-blue.svg)

</div>

## Directory Structure
```
├── README.md          <- The top-level README.
│
├── assets             <- Static files for project. 
│
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default Sphinx project; see sphinx-doc.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-hz-topic_modeling`.
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.py           <- Make this project pip installable with `pip install -e`
│
├── src                <- Source code for use in this project.
│   ├── __init__.py    <- Makes src a Python module
│   │
│   ├── apps           <- Keeps all modules in apps folder
│   │    └──xxx_app    <- Scripts to run a module/pipeline. see details in Framework section
│   │
│   ├── base           <- Defines abstract pipelines/classes/methods and database base classes
│   │
│   ├── models         <- Scripts to train models or use trained models to make predictions
│   │
│   └── utils          <- Scripts for logging, UI, etc.
│
└── tests              <- Source code for testing, follows src structure.