import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import HomePage from '../pages/HomePage'
import JurisdictionsPage from '../pages/JurisdictionsPage'
import JurisdictionPage from '../pages/JurisdictionPage'
import VenuePage from '../pages/VenuePage'
import MatrixPage from '../pages/MatrixPage'
import ParametersPage from '../pages/ParametersPage'
import ParameterPage from '../pages/ParameterPage'
import NotFoundPage from '../pages/NotFoundPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'jurisdictions', element: <JurisdictionsPage /> },
      { path: 'jurisdictions/:nameRu', element: <JurisdictionPage /> },
      { path: 'venues/:venueKey', element: <VenuePage /> },
      { path: 'venues/:venueKey/matrix/:cellId', element: <MatrixPage /> },
      { path: 'parameters', element: <ParametersPage /> },
      { path: 'parameters/:parameterId', element: <ParameterPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
