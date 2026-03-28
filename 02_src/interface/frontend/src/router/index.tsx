import { createBrowserRouter, Navigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import HomePage from '../pages/HomePage'
import JurisdictionsPage from '../pages/JurisdictionsPage'
import JurisdictionPage from '../pages/JurisdictionPage'
import VenuePage from '../pages/VenuePage'
import CellDetailPage from '../pages/CellDetailPage'
import MatrixPage from '../pages/MatrixPage'
import InstrumentsPage from '../pages/InstrumentsPage'
import MethodologyPage from '../pages/MethodologyPage'
import AnalysisPage from '../pages/AnalysisPage'
import NotFoundPage from '../pages/NotFoundPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'jurisdictions', element: <JurisdictionsPage /> },
      { path: 'jurisdictions/:nameRu', element: <JurisdictionPage /> },
      { path: 'venues/:venueKey/:cellId', element: <CellDetailPage /> },
      { path: 'venues/:venueKey', element: <VenuePage /> },
      { path: 'venues/:venueKey/matrix/:cellId', element: <MatrixPage /> },
      { path: 'instruments', element: <InstrumentsPage /> },
      { path: 'methodology', element: <MethodologyPage /> },
      { path: 'analysis', element: <AnalysisPage /> },
      { path: 'parameters', element: <Navigate to="/instruments" replace /> },
      { path: 'parameters/:parameterId', element: <Navigate to="/instruments" replace /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
