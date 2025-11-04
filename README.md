🧭 Recomendador de Rutas · Coach Vocacional (Demo IA con Streamlit + RAG)
🧩 Descripción general

Este demo es un asistente inteligente y evocador que conversa con el usuario para descubrir sus intereses, estilo personal y motivaciones, y a partir de esa conversación recomienda un camino de aprendizaje (o training path) proveniente de distintas instituciones públicas y privadas.

El sistema funciona como un coach vocacional y orientador personal, capaz de guiar incluso a quienes no saben por dónde empezar, sugiriendo cursos y rutas que combinan tanto la afinidad psicológica del usuario como la correspondencia técnica del catálogo.

💡 Principales características
Módulo	Descripción
🧠 Chat Evocador	Conversación natural: “¿Cómo estás?”, “Cuéntame sobre ti”, “¿Qué te motiva últimamente?” — va llenando un perfil dinámico de intereses, estilo, valores, metas y tiempo disponible.
🔍 RAG Híbrido (TF-IDF + BM25)	Recupera cursos relevantes del catálogo Excel combinando búsqueda semántica y exacta.
⚖️ Ranking Heurístico Inteligente	Pondera coincidencias por área, nivel, acceso, duración y palabras clave.
🎯 Campos Dependientes	Al elegir un área o categoría, se actualizan subcampos (nivel, acceso, población) automáticamente.
🤖 ChatOpenAI Integrado	Genera explicaciones, acompaña el diálogo y redacta la narrativa final del track. Incluye fallback local si no hay API Key.
📄 Exportación PDF	El usuario puede descargar su ruta recomendada con resumen de perfil y detalles por curso.
🪄 Diseño Escalable	Preparado para evolucionar a ranking con aprendizaje (LTR), recomendación colaborativa tipo Netflix y bandits contextuales.
🏗️ Arquitectura
app_streamlit.py      → UI principal (chat + resultados + PDF)
config.py             → Config global (pesos, paths, constantes)
rag_build.py          → Carga y normalización de catálogos Excel
                         + índice híbrido (BM25 + TF-IDF)
ranker.py             → Features + puntuación ponderada de candidatos
chat_orchestrator.py  → Perfil de usuario + flujo de conversación
pdf_utils.py          → Generación del PDF final
cf_bandit.py          → Placeholder para recomendador colaborativo futuro
requirements.txt      → Dependencias
README.md             → Este archivo

⚙️ Instalación y ejecución

1️⃣ Clonar el repo o copiar los archivos

git clone https://github.com/tuusuario/recomendador-coach.git
cd recomendador-coach


2️⃣ Instalar dependencias

pip install -r requirements.txt


3️⃣ Ejecutar la app

streamlit run app_streamlit.py


4️⃣ Subir el catálogo Excel
Puedes usar el archivo CONTENIDOS ATENEA PARA RAG.xlsx (si está disponible en el entorno) o subir uno propio con estructura similar:

Portal o Aliado

Tipo de Acceso (REA o Redireccionamiento)

Grupo de Competencias

Curso

Descripción del Curso

Nivel de complejidad

Duración del Curso

URL del Curso

Palabras Clave

Población objetivo
(entre otros campos)

💬 Cómo funciona el flujo

El chat inicia la conversación con tono humano (“Hola, ¿cómo estás?”, “¿Qué te motiva?”).

El sistema extrae información implícita (edad, intereses, estilo de aprendizaje, valores).

Genera una consulta híbrida RAG que busca cursos relevantes según el perfil.

Aplica un ranking ponderado para seleccionar el Top-N más coherente con el usuario.

El asistente explica la ruta sugerida en lenguaje natural (“Empezamos con fundamentos de IA y luego proyectos aplicados…”).

El usuario puede ajustar preferencias (“Quisiera algo más creativo”) y el sistema re-evalúa el path.

Finalmente, el usuario descarga su ruta en PDF con todo el detalle y justificación.

🤝 Extensiones futuras
Fase	Funcionalidad	Descripción
🧩 RAG Semántico	Integrar embeddings (FAISS/Chroma) y sinónimos dinámicos.	
🪄 LTR (Learning-to-Rank)	Ajustar pesos automáticamente según feedback de usuarios (clicks, “me gustó”).	
🎞️ Recomendador Colaborativo	Modelo tipo Netflix: aprende patrones de usuarios similares (ALS o LightFM).	
🎯 Bandits Contextuales	Optimiza orden y exploración (LinUCB, Thompson Sampling).	
📊 Panel Admin	Ajustar pesos, revisar métricas, monitorear feedback.	
🔐 Multi-organización	Personalización por institución (filtros, identidad visual).	
🧮 Modelo de ranking (actual)

El sistema asigna un score ponderado a cada curso:

score
=
∑
𝑖
𝑤
𝑖
⋅
𝑓
𝑖
score=
i
∑
	​

w
i
	​

⋅f
i
	​

Feature	Descripción	Peso
area_exact	Coincidencia exacta de área o grupo de competencias	3.0
sheet_match	Coincidencia con categoría (hoja)	2.0
level	Nivel de complejidad (básico/intermedio/avanzado)	2.0
duration_fit	Duración ≤ máximo de horas	1.0
access	Tipo de acceso preferido	1.0
population	Coincidencia de población objetivo	1.0
kw_overlap	Palabras clave coincidentes (máx. 4)	1.0 por hit
sim_tfidf	Similitud semántica TF-IDF	2.0
sim_bm25	Relevancia textual BM25	1.5

Luego se re-ordena por score descendente → se presenta el Top-N (12) cursos como ruta inicial.

📈 Beneficios técnicos y comerciales
Perspectiva	Valor
💬 UX natural	El usuario siente que habla con un orientador real, no con un formulario.
🧠 Razonamiento híbrido	Combina semántica (RAG) con estructura (filtros y metadata).
🪶 Ligero y escalable	100 % en Python, sin bases de datos externas para el PoC.
🔎 Transparente y explicable	Cada curso incluye “por qué aparece” y cómo se calculó el score.
💼 Listo para demos institucionales	Ideal para Ministerios, agencias de empleo, universidades o portales de formación.
🚀 Evolutivo	Facilita integrar IA generativa, analítica de uso y recomendaciones colaborativas.
🧰 Variables clave

ProfileState: representa el perfil del usuario en tiempo real (edad, intereses, valores, estilo, etc.).

RAGIndex: maneja búsqueda híbrida (BM25 + TF-IDF) sobre el catálogo.

rerank: aplica pesos heurísticos para ordenar candidatos.

ChatOpenAI: wrapper para orquestar diálogo y generar explicaciones.

build_path_pdf: exporta resultados con formato profesional.

📚 Requisitos mínimos

Python 3.10+

Streamlit ≥ 1.37

Pandas, scikit-learn, rank-bm25, reportlab

No requiere clave de API para correr el demo.
Si defines la variable OPENAI_API_KEY, el chat usará un modelo real de OpenAI.

🧑‍💼 Autor y uso

Proyecto IA – Aplicativo de recomendación de rutas de capacitación.
Desarrollado para demostrar capacidades de RAG + Conversación Evocadora + Ranking Inteligente aplicadas al sector educativo y formativo.

👤 Lead IA Developer: [Tu nombre o equipo]
📧 Contacto: [tu.email@organizacion.com
]

🪞 Capturas sugeridas (para README visual)

(No incluidas en este texto, pero sugerido para presentación)

🗨️ Pantalla del chat evocador.

🔍 Ejemplo de resultados de cursos.

📄 PDF exportado con perfil resumido.

🧩 Diagrama de flujo RAG → Ranking → Chat → PDF.