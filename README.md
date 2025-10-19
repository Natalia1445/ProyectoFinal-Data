# ProyectoFinal-Data
# Amazon vs Goodreads: ¿Los compradores y lectores están de acuerdo?

Proyecto final del curso de AWS Data Engineering - porque necesitaba saber si Amazon me está mintiendo sobre qué libros son buenos.

## El Problema

¿Alguna vez compraste un libro con 5 estrellas en Amazon y resultó ser malísimo? Yo sí. Muchas veces.

Resulta que Amazon no solo vende libros - vende TODO. Y la gente califica basándose en si llegó rápido, si el empaque estaba bonito, o si el precio estuvo bien. No necesariamente si el libro es bueno.

Goodreads, por otro lado,es una plataforma de lectores.. Terminan el libro y califican la historia o calidad literaria

**Entonces la pregunta es:** ¿Qué tan diferente es realmente? ¿Vale la pena checar ambos sitios antes de comprar?


## Qué hice

Construí un pipeline completo en AWS para analizar esto:

- **758 libros** que existen en ambas plataformas
- **51 outliers** donde las calificaciones están súper diferentes (>2 puntos)
- **0.89 puntos** de diferencia promedio

### Los datos

- Amazon: 500,000 reviews 
- Goodreads: 11,000 libros con ratings

### El pipeline

S3 (datos crudos)
  ↓
Lambda 1: Limpiar y agregar reviews de Amazon
  ↓
Lambda 2: Matchear libros entre plataformas (el más difícil)
  ↓
Lambda 3: Calcular diferencias y outliers
  ↓
MySQL + S3 (resultados)
  ↓
Dashboard en Streamlit


## Lo que aprendí

### 1. Matchear por título no es suficiente

Primer intento: "Anna Karenina" en Amazon = "Anna Karenina" en Goodreads

Problema: Uno es la novela de Tolstoy, el otro es material de estudio de Cara Delevingne.

Solución: Validación de autores con fuzzy matching. 135 matches falsos eliminados.

### 2. Los datos están sucios

- Precios en formato raro
- Ratings en diferentes escalas (1-5 vs 1-10)
- Títulos con "The", sin "The", con caracteres especiales
- NaN por todos lados

Pasé más tiempo limpiando que programando.

### 3. Lambda tiene límites de memoria

Procesar 500k reviews de golpe = 💥

Solución: Chunks de 10k. Más lento pero funciona.

## Hallazgos interesantes

- **Amazon califica 0.9 puntos más alto** en promedio. Sesgo comercial confirmado.
- **Precio no predice calidad.** Correlación débil (0.28). Los libros caros no son mejores.
- **51 libros** tienen rating muy alto en Amazon pero bajo en Goodreads. Éxitos comerciales, fracasos literarios.

## Tech Stack

**Cloud:**
- AWS Lambda (Python 3.11)
- S3 para almacenamiento
- RDS MySQL para datos finales
- GitHub Actions para CI/CD

**Código:**
- Python, Pandas (obvio)
- Plotly para gráficas
- Streamlit para el dashboard
- FuzzyWuzzy para matching de autores

**DevOps:**
- Self-hosted runner en EC2
- Deploy automático en cada push

## Cómo correr esto

### Si solo quieres ver el dashboard:

[URL del dashboard aquí cuando esté deployed]

### Si quieres correr el pipeline:

Necesitas:
- Cuenta AWS con Lambda, S3, RDS
- Credenciales configuradas
- Mucha paciencia
```bash
# Subir datos a S3
aws s3 cp amazon_reviews.csv s3://tu-bucket/raw/
aws s3 cp goodreads_books.csv s3://tu-bucket/raw/

# Ejecutar lambdas en orden
# (o esperar el trigger automático)

# Ver resultados en dashboard
streamlit run app.py
```

## Estructura del proyecto
```
├── lambda_1_extract.py       # Limpia Amazon reviews
├── lambda_2_transform.py     # Matchea libros
├── lambda_3_load.py          # Calcula y carga a DB
├── app.py                    # Dashboard
├── requirements.txt
└── .github/
    └── workflows/
        └── deploy.yml        # Auto-deploy
```

## Challenges que me quitaron el sueño

1. **El matching de libros**
   - Título + autor no siempre funciona
   - Ediciones diferentes del mismo libro
   - Traducciones con nombres diferentes

2. **Normalizar ratings**
   - Amazon: 1-5 estrellas
   - Goodreads: 1-5 estrellas también
   - Pero distribuidos MUY diferente
   - Solución: escalar a 0-10 y normalizar

3. **Precio**
   - Solo 111 libros tienen precio
   - NaN everywhere
   - Decidí no usarlo como filtro

## Si tuviera más tiempo

- Machine Learning para predecir outliers
- Sentiment analysis de reviews (no solo ratings)
- Más plataformas (Barnes & Noble, Apple Books)
- Tracking histórico - ¿cómo cambian los ratings con el tiempo?

## El Dashboard

Tiene:
- Scatter plot interactivo (Goodreads vs Amazon)
- Filtros por rating
- Top 10 mayores discrepancias
- Análisis de precio (para los que tienen)
- Búsqueda de libros

Lo que NO tiene:
- Diseño súper fancy (funcional > bonito)
- Animaciones locas
- Gráficas 3D innecesarias

## Conclusión

No confíes solo en Amazon. Si un libro tiene 5 estrellas ahí pero 3 en Goodreads, probablemente es marketing.

Usa ambas plataformas. O mejor: usa este dashboard.

---

**Hecho con ☕ y muchas horas de debugging**

Natalia Esquivel  
AWS Data Engineering Course 2025

P.D. Si encuentras un bug, probablemente ya lo sé pero no tuve tiempo de arreglarlo.
