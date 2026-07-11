import './App.css'
import Hero from './components/Hero';
import Queue from './components/Queue';

function App() {
  const userId = localStorage.getItem('userId');

  return (
    <div className='h-full w-full flex flex-col'>
      {!userId && <Hero />}
      {userId && <Queue />}
    </div>
  )
}

export default App
