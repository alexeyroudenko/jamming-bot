import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppContent } from './App';

// react-force-graph ships ESM; Jest does not transform it without extra config.
jest.mock('./pages/semantic', () => ({
  __esModule: true,
  default: function SemanticPlaceholder() {
    return null;
  },
}));

jest.mock('./components/Steps', () => ({
  __esModule: true,
  default: function StepsPlaceholder() {
    return null;
  },
}));

jest.mock('./pages/atlas', () => ({
  __esModule: true,
  default: function AtlasPlaceholder() {
    return null;
  },
}));

test('renders main nav', () => {
  render(
    <MemoryRouter basename="/scenes" initialEntries={['/']}>
      <AppContent />
    </MemoryRouter>
  );
  expect(screen.getByRole('link', { name: 'Semantic' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Tags' })).toBeInTheDocument();
});
