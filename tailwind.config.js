module.exports = {
  content: [
    '*.{html,js}',
  ],
  theme: {
    fontFamily: {
      mono: ['Source Code Pro', 'mono'],
    },
  },
  daisyui: {
    themes: [
      {
        spack: {
          "primary": "#103b7f",
          "secondary": "#ffa701",
          "accent": "#2f7d95",
          "neutral": "#374151",
          "base-100": "#ffffff",
          "info": "#bfdbfe",
          "success": "#d9f99d",
          "warning": "#fde68a",
          "error": "#fecaca",
          "--rounded-box": "5px", // border radius rounded-box utility class, used in card and other large boxes
          "--rounded-btn": "5px", // border radius rounded-btn utility class, used in buttons and similar element
        },
      },
    ],
  },
  plugins: [require('daisyui')],
};
