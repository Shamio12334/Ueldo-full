let currentTemplate = 1;

// Image Sources (You can host your own specific images later)
const templates = {
    1: {
        src: 'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?q=80&w=1080&auto=format&fit=crop', // A Dark Stadium Background
        textColor: '#FFFFFF',
        accentColor: '#00ff99' // Neon Green
    },
    2: {
        src: 'https://images.unsplash.com/photo-1513364776144-60967b0f800f?q=80&w=1080&auto=format&fit=crop', // A Bright Artistic Background
        textColor: '#1a1a2e',
        accentColor: '#ff0055' // Hot Pink
    }
};

function selectTemplate(id, element) {
    currentTemplate = id;
    document.getElementById('selectedTemplateId').value = id;
    
    // UI Update
    document.querySelectorAll('.template-option').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
}

function generateProPoster() {
    const canvas = document.getElementById('myCanvas');
    const ctx = canvas.getContext('2d');
    
    // Get Data
    const name = document.getElementById('compName').value || "CHAMPIONSHIP";
    const subCat = document.getElementById('subCat').value || "EVENT";
    const date = document.getElementById('dateTime').value || "Coming Soon";
    const fee = document.getElementById('fee').value || "FREE";
    const prize = document.getElementById('prize').value || "WIN GLORY";
    const venue = document.getElementById('venue').value || "Kolkata";

    // Load Background Image First
    const bgImage = new Image();
    bgImage.crossOrigin = "anonymous"; // Important for downloading
    bgImage.src = templates[currentTemplate].src;

    bgImage.onload = function() {
        // 1. Draw Background
        ctx.drawImage(bgImage, 0, 0, 1080, 1350);

        // 2. Add a Dark Overlay (So text is readable)
        ctx.fillStyle = (currentTemplate === 1) ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.7)';
        ctx.fillRect(50, 50, 980, 1250); // Frame effect

        // 3. Setup Text Styles
        const mainColor = templates[currentTemplate].textColor;
        const accent = templates[currentTemplate].accentColor;
        
        ctx.textAlign = 'center';

        // --- DRAW TEXT ---

        // Sub Category (Top Small)
        ctx.font = 'bold 50px Poppins, sans-serif';
        ctx.fillStyle = accent;
        ctx.fillText(subCat.toUpperCase(), 540, 200);

        // Competition Name (Big & Bold)
        ctx.font = '900 100px Poppins, sans-serif';
        ctx.fillStyle = mainColor;
        
        // Wrap text if too long
        if(name.length > 15) {
            const words = name.split(' ');
            ctx.fillText(words.slice(0, words.length/2).join(' '), 540, 350);
            ctx.fillText(words.slice(words.length/2).join(' '), 540, 460);
        } else {
            ctx.fillText(name, 540, 400);
        }

        // Prize Box
        ctx.fillStyle = accent;
        ctx.fillRect(240, 550, 600, 10); // Separator Line
        
        ctx.font = 'bold 70px Poppins, sans-serif';
        ctx.fillStyle = mainColor;
        ctx.fillText("PRIZE POOL", 540, 640);
        
        ctx.font = '900 110px Poppins, sans-serif';
        ctx.fillStyle = accent;
        ctx.fillText(prize, 540, 760);

        // Details (Date & Venue)
        ctx.font = '50px Poppins, sans-serif';
        ctx.fillStyle = mainColor;
        ctx.fillText("📅 " + date, 540, 950);
        ctx.fillText("📍 " + venue, 540, 1030);

        // Entry Fee Badge
        ctx.beginPath();
        ctx.fillStyle = mainColor;
        ctx.roundRect(340, 1120, 400, 100, 50);
        ctx.fill();
        
        ctx.fillStyle = (currentTemplate === 1) ? '#000' : '#FFF'; // Text color inside badge
        ctx.font = 'bold 50px Poppins, sans-serif';
        ctx.fillText("ENTRY: ₹" + fee, 540, 1185);

        // Show the result
        document.getElementById('posterArea').style.display = 'block';
        document.getElementById('posterArea').scrollIntoView({behavior: "smooth"});
    };
}

function downloadPoster() {
    const link = document.createElement('a');
    link.download = 'ueldo-poster.png';
    link.href = document.getElementById('myCanvas').toDataURL();
    link.click();
}