const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

const Hero = () => {
    const handleClick = async () => {
        const userId = localStorage.getItem('userId');
        if (userId) return;
        localStorage.setItem('userId', crypto.randomUUID());
        const res = await fetch(`${BACKEND_URL}/api/username`);
        const data = await res.json();
        localStorage.setItem('username', data.username);
    };
    return <section>
        <h1>AI Spy</h1>
        <p>Lorem ipsum dolor, sit amet consectetur adipisicing elit. Facere, quaerat vero maiores iure corporis repellat impedit qui modi omnis placeat obcaecati voluptate voluptas fugiat sunt reprehenderit beatae id! Quaerat, maxime.</p>
        <button onClick={handleClick}>Play now!</button>
    </section>
};
 
export default Hero;