import { createTheme } from '@mui/material/styles'

const steel = {
  950: '#090b0e',
  900: '#11151b',
  850: '#161b22',
  800: '#1b222b',
  700: '#27303b',
  600: '#33404e',
  500: '#4a5c6d',
}

export const appTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#f59e0b',
      light: '#fbbf24',
      dark: '#b45309',
    },
    secondary: {
      main: '#22d3ee',
    },
    background: {
      default: steel[950],
      paper: steel[900],
    },
    text: {
      primary: '#e5e7eb',
      secondary: '#94a3b8',
    },
    success: {
      main: '#22c55e',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#ef4444',
    },
    divider: steel[700],
  },
  shape: {
    borderRadius: 10,
  },
  typography: {
    fontFamily: 'Rajdhani, Segoe UI, sans-serif',
    h4: {
      fontWeight: 700,
      letterSpacing: '0.06em',
    },
    h5: {
      fontWeight: 600,
      letterSpacing: '0.04em',
    },
    subtitle2: {
      fontFamily: 'IBM Plex Mono, Consolas, monospace',
      letterSpacing: '0.05em',
    },
    button: {
      fontWeight: 700,
      letterSpacing: '0.04em',
      textTransform: 'none',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: steel[950],
          backgroundImage:
            'radial-gradient(circle at 25% 20%, rgba(251, 191, 36, 0.1), transparent 45%), radial-gradient(circle at 90% 0%, rgba(34, 211, 238, 0.08), transparent 35%), repeating-linear-gradient(120deg, rgba(148, 163, 184, 0.06), rgba(148, 163, 184, 0.06) 1px, transparent 1px, transparent 14px)',
          backgroundAttachment: 'fixed',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          border: `1px solid ${steel[700]}`,
          backgroundImage: `linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0))`,
          boxShadow: `0 18px 32px rgba(0, 0, 0, 0.35)`,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: steel[850],
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontFamily: 'IBM Plex Mono, Consolas, monospace',
          borderRadius: 6,
        },
      },
    },
  },
})
