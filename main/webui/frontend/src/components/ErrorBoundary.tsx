import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught React UI error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '32px', maxWidth: '800px', margin: '40px auto', background: 'var(--bg-card)', border: '1px solid var(--danger)', borderRadius: '10px' }}>
          <h2 style={{ color: 'var(--danger)', marginBottom: '12px', fontSize: '18px' }}>
            UI Render Notice
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '16px' }}>
            A temporary component error occurred while rendering the data:
          </p>
          <pre style={{ background: '#050810', padding: '12px', borderRadius: '6px', color: '#f87171', fontSize: '13px', overflowX: 'auto', marginBottom: '16px' }}>
            {this.state.error?.message || 'Unknown render error'}
          </pre>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
          >
            Reload UI
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
