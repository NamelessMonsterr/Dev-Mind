/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  safelist: [
    // Mountain lake colors - safelist to ensure compilation
    { pattern: /^(bg|text|border|from|via|to|shadow)-(coral|teal|mint|peach|navy)(-\d+)?$/ },
    'bg-gradient-to-br',
    'bg-gradient-to-r',
    'bg-clip-text',
    'text-transparent',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
      // Mountain Lake Color Palette
      border: "hsl(var(--border))",
      input: "hsl(var(--input))",
      ring: "hsl(210 100% 60%)",
      background: "hsl(var(--background))",
      foreground: "hsl(var(--foreground))",
      
      // Coral - Primary accent
      coral: {
        50: '#FEF2F2',
        100: '#FCE4E4',
        200: '#FACBCA',
        300: '#F5A6A5',
        400: '#EE8483',
        DEFAULT: '#E27D7C',
        600: '#D05F5E',
        700: '#B04746',
        800: '#8F3938',
        900: '#6F2C2B',
      },
      
      // Light Pink/Peach - Secondary
      peach: {
        50: '#FFF5F3',
        100: '#FFE9E5',
        200: '#FFD3CC',
        300: '#FFB8AD',
        DEFAULT: '#F0A9A0',
        500: '#E89588',
        600: '#D97B6C',
        700: '#C66152',
        800: '#A94C3F',
        900: '#8A3C32',
      },
      
      // Mint Green - Success/Tertiary
      mint: {
        50: '#F4F9F6',
        100: '#E8F3EC',
        200: '#D1E7D9',
        DEFAULT: '#B8D4BC',
        400: '#9FC2A5',
        500: '#86B08E',
        600: '#6D9E77',
        700: '#578665',
        800: '#456B51',
        900: '#35523E',
      },
      
      // Teal - Info/Links
      teal: {
        50: '#F0F7F9',
        100: '#E0EFF3',
        200: '#C2DFE7',
        300: '#A3CFDB',
        400: '#84BFCF',
        DEFAULT: '#5B9AA9',
        600: '#4A8594',
        700: '#3C6D7A',
        800: '#2F5661',
        900: '#234048',
      },
      
      // Navy - Dark backgrounds
      navy: {
        50: '#F5F7F8',
        100: '#EAEEF1',
        200: '#D5DDE3',
        300: '#B0BCC7',
        400: '#8B9BAB',
        500: '#667A8F',
        600: '#4F6178',
        700: '#3E4D5F',
        DEFAULT: '#2E4057',
        900: '#1F2B3A',
      },
      
      primary: {
        DEFAULT: '#E27D7C',
        foreground: '#FFFFFF',
      },
      secondary: {
        DEFAULT: '#B8D4BC',
        foreground: '#2E4057',
      },
      destructive: {
        DEFAULT: '#EF4444',
        foreground: '#FFFFFF',
      },
      muted: {
        DEFAULT: '#F0F7F9',
        foreground: '#667A8F',
      },
      accent: {
        DEFAULT: '#5B9AA9',
        foreground: '#FFFFFF',
      },
      popover: {
        DEFAULT: '#FFFFFF',
        foreground: '#2E4057',
      },
      card: {
        DEFAULT: '#FFFFFF',
        foreground: '#2E4057',
      },
    },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")]
}
