import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import SharedPage from './pages/SharedPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/chat/:id" element={<ChatPage />} />
      <Route path="/shared/:token" element={<SharedPage />} />
    </Routes>
  )
}

export default App
