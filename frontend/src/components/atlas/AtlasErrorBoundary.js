import React from 'react';

/**
 * Isolates atlas D3 charts so a throw in one effect does not unmount the whole SPA.
 */
export default class AtlasErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { err: null };
  }

  static getDerivedStateFromError(err) {
    return { err };
  }

  componentDidCatch(err, info) {
    console.error('Atlas chart error:', this.props.label || 'chart', err, info.componentStack);
  }

  render() {
    if (this.state.err) {
      const msg = this.state.err.message || String(this.state.err);
      return (
        <div className="atlas-banner atlas-banner--err" role="alert">
          {this.props.label ? `${this.props.label}: ` : ''}
          {msg}
        </div>
      );
    }
    return this.props.children;
  }
}
