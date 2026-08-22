/**
 * Easing functions for the data-driven timeline.
 *
 * Mirrors the TextSceneSpec ANIMATION_EASINGS enum exactly. Pure functions of
 * progress p in [0, 1] — no state, no allocation, fully scrubbable.
 */

export const EASINGS = {
  linear: (p) => p,

  easeIn: (p) => p * p,
  easeOut: (p) => 1 - (1 - p) * (1 - p),
  easeInOut: (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2),

  easeInQuad: (p) => p * p,
  easeOutQuad: (p) => 1 - (1 - p) * (1 - p),
  easeInOutQuad: (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2),

  easeInCubic: (p) => p * p * p,
  easeOutCubic: (p) => 1 - Math.pow(1 - p, 3),
  easeInOutCubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),

  easeInSine: (p) => 1 - Math.cos((p * Math.PI) / 2),
  easeOutSine: (p) => Math.sin((p * Math.PI) / 2),
  easeInOutSine: (p) => -(Math.cos(Math.PI * p) - 1) / 2,

  easeInExpo: (p) => (p === 0 ? 0 : Math.pow(2, 10 * p - 10)),
  easeOutExpo: (p) => (p === 1 ? 1 : 1 - Math.pow(2, -10 * p)),
  easeInOutExpo: (p) => {
    if (p === 0) return 0;
    if (p === 1) return 1;
    return p < 0.5 ? Math.pow(2, 20 * p - 10) / 2 : (2 - Math.pow(2, -20 * p + 10)) / 2;
  },

  easeInBack: (p) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return c3 * p * p * p - c1 * p * p;
  },
  easeOutBack: (p) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2);
  },
  easeInOutBack: (p) => {
    const c2 = 1.70158 * 1.525;
    return p < 0.5
      ? (Math.pow(2 * p, 2) * ((c2 + 1) * 2 * p - c2)) / 2
      : (Math.pow(2 * p - 2, 2) * ((c2 + 1) * (p * 2 - 2) + c2) + 2) / 2;
  },

  easeInElastic: (p) => {
    const c4 = (2 * Math.PI) / 3;
    return p === 0 ? 0 : p === 1 ? 1 : -Math.pow(2, 10 * p - 10) * Math.sin((p * 10 - 10.75) * c4);
  },
  easeOutElastic: (p) => {
    const c4 = (2 * Math.PI) / 3;
    return p === 0 ? 0 : p === 1 ? 1 : Math.pow(2, -10 * p) * Math.sin((p * 10 - 0.75) * c4) + 1;
  },
  easeInOutElastic: (p) => {
    const c5 = (2 * Math.PI) / 4.5;
    if (p === 0) return 0;
    if (p === 1) return 1;
    return p < 0.5
      ? -(Math.pow(2, 20 * p - 10) * Math.sin((20 * p - 11.125) * c5)) / 2
      : (Math.pow(2, -20 * p + 10) * Math.sin((20 * p - 11.125) * c5)) / 2 + 1;
  },

  easeInBounce: (p) => 1 - bounceOut(1 - p),
  easeOutBounce: bounceOut,
  easeInOutBounce: (p) =>
    p < 0.5 ? (1 - bounceOut(1 - 2 * p)) / 2 : (1 + bounceOut(2 * p - 1)) / 2,
};

function bounceOut(p) {
  const n1 = 7.5625;
  const d1 = 2.75;
  if (p < 1 / d1) return n1 * p * p;
  if (p < 2 / d1) return n1 * (p -= 1.5 / d1) * p + 0.75;
  if (p < 2.5 / d1) return n1 * (p -= 2.25 / d1) * p + 0.9375;
  return n1 * (p -= 2.625 / d1) * p + 0.984375;
}

/** Resolve an easing name to a function; unknown names fall back to linear. */
export function getEasing(name) {
  return EASINGS[name] ?? EASINGS.linear;
}