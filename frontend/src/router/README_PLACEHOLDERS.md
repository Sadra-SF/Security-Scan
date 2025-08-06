These TypeScript errors are expected until Node.js and dependencies are installed.

What you will do after installing Node/npm:
1) In a terminal:
   cd security-scanner/frontend
   npm install
2) Start dev server:
   npm run dev

Why errors show now:
- Imports like react, react-router-dom, @tanstack/react-query, zustand, tailwindcss types are unresolved until node_modules is installed.
- JSX typings come from React's type packages and vite's client types, both installed by npm.

Temporary scaffolding choices:
- src/router/_tempPlaceholders.tsx provides no-JSX null components to keep router wiring in place.
- Real pages are in src/pages/... and will resolve after install.