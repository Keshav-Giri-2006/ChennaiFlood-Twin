import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  label: string
  children: ReactNode
}

/** Keeps one failing panel from taking down the whole Digital Twin (docs/07 §104). */
export class ErrorBoundary extends Component<Props, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[${this.props.label}]`, error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="panel error-panel" role="alert">
          <strong>{this.props.label} unavailable</strong>
          <p className="small">{this.state.error.message}</p>
        </div>
      )
    }
    return this.props.children
  }
}
