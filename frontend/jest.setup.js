import '@testing-library/jest-dom';

// Mock matchMedia for recharts/responsive layouts components checks
global.matchMedia = global.matchMedia || function() {
  return {
    matches: false,
    addListener: function() {},
    removeListener: function() {}
  };
};
