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
    <MemoryRouter basename="/static-app" initialEntries={['/static-app/']}>
      <AppContent />
    </MemoryRouter>
  );
  expect(screen.getByText(/Semantic cloud/i)).toBeInTheDocument();
  expect(screen.getByText(/Data Atlas/i)).toBeInTheDocument();
});
