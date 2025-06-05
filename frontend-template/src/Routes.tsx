import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Import page components
import SwiperChatApplicationPage from './pages/SwiperChatApplication';

const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<SwiperChatApplicationPage />} />
      </Routes>
    </Router>
  );
};

export default AppRoutes;