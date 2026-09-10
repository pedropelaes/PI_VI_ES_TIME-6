import '@testing-library/jest-dom/vitest';

// jsdom nao implementa a API de object URL usada para previews de arquivo.
if (typeof URL.createObjectURL !== 'function') {
  URL.createObjectURL = () => 'blob:mock-url';
}
if (typeof URL.revokeObjectURL !== 'function') {
  URL.revokeObjectURL = () => {};
}
