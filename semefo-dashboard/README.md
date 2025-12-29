# SEMEFO Dashboard

## Descripción

Este proyecto es un dashboard administrativo desarrollado con Vue 3 para el sistema SEMEFO (Servicio Médico Forense). La aplicación proporciona una interfaz web moderna para la gestión y visualización de datos del sistema forense.

## Funcionalidades Principales

- 📊 Visualización de estadísticas y métricas del sistema
- 👥 Gestión de usuarios y permisos
- 📝 Administración de registros forenses
- 🔍 Búsqueda y filtrado de información
- 📈 Generación de reportes
- 🔐 Sistema de autenticación seguro

## Tecnologías Utilizadas

- **Vue 3** - Framework JavaScript progresivo con Composition API
- **TypeScript** - Tipado estático para JavaScript
- **Vite** - Herramienta de build rápida y moderna

## Requisitos Previos

- Node.js (versión 16 o superior)
- npm o yarn
- Servidor backend SEMEFO corriendo

## Instalación

```bash
# Clonar el repositorio
git clone [URL_DEL_REPOSITORIO]

# Navegar al directorio
cd semefo-dashboard

# Instalar dependencias
npm install
```

## Configuración

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
VITE_API_URL=http://localhost:3000/api
VITE_APP_TITLE=SEMEFO Dashboard
```

## Ejecución

```bash
# Modo desarrollo
npm run dev

# Build para producción
npm run build

# Preview del build de producción
npm run preview
```

## Estructura del Proyecto

```
semefo-dashboard/
├── src/
│   ├── assets/         # Recursos estáticos
│   ├── components/     # Componentes Vue reutilizables
│   ├── views/          # Páginas/Vistas principales
│   ├── types/          # Definiciones TypeScript
│   └── utils/          # Funciones auxiliares
├── public/             # Archivos públicos
└── index.html          # Punto de entrada HTML
```

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto es privado y confidencial. Todos los derechos reservados.
