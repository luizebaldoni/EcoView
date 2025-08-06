# EcoView Sistema de visualização de dados em tempo real

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)

Sistema completo para coleta, armazenamento e visualização de dados em tempo real de sistemas desenvolvidos pelo Grupo de Pesquisas em Modelagem HidroAmbiental e Ecotecnologias da UFSM.

## Funcionalidades

- **Coleta de dados em tempo real** via API REST
- **Dashboard interativo** com visualizações Chart.js
- **Gerenciamento de dados** com tabelas paginadas e filtros
- **Multi-dispositivos** acompanhamento de vários sensores
- **Exportação de dados** (CSV, JSON, Excel)
- **Atualização de Firmware** Over the Air (OTA)

## 🛠️ Tecnologias Utilizadas

| Componente | Tecnologias                                                         |
|------------|---------------------------------------------------------------------|
| Backend    | Python 3.9+, Django 4.2, Django REST Framework, SQLite              |
| Firmware   | C++ (Arduino Core), ESP32                                           |
| Frontend   | HTML5, Bootstrap 5, Chart.js (para gráficos de histórico)           |
| Sensores | DS18B20, DHT-11, UV, ANEMOMETRO|

## Arquitetura de Software
```mermaid
---
config:
  layout: dagre
---
flowchart TD
    E["Views.py"] -- Show data graphs --> A["Frontend: Dashboard Web"]
    B["API: Django Backend"] -- Validating and processing --> C["Models.py"]
    C -- Save and recover --> D[("SQLite")]
    D -- Search and show --> C
    B -- Send POST --> E
    F["Hardware: ESP32"] -- Converted and packed --> H["Json File"]
    H -- Send data_sensors --> B
    G["Sensors"] -- Analog or digital Sinal --> F
     E:::Backend
     E:::Backend
     A:::Frontend
     A:::Frontend
     B:::Backend
     B:::Backend
     C:::Backend
     C:::Backend
     D:::Banco
     D:::Banco
     F:::Hardware
     F:::Hardware
     H:::Aqua
     G:::Hardware
    classDef Backend fill:#f9f,stroke:#333,stroke-width:2px
    classDef Frontend fill:#ccf,stroke:#333,stroke-width:2px
    classDef Banco fill:#cff,stroke:#333,stroke-width:2px
    classDef Hardware fill:#FFE0B2, color:#000000
    classDef Aqua stroke-width:1px, stroke-dasharray:none, stroke:#46EDC8, fill:#DEFFF8, color:#378E7A
    style G stroke:#000000
```