// Request permission once
if (Notification.permission !== "granted") {
  Notification.requestPermission();
}

// Poll server every 30 seconds
setInterval(() => {
  fetch("/check_reminder")
    .then(res => res.json())
    .then(meds => {
      meds.forEach(m => {
        showMedicineNotification(m.name, m.dosage);
      });
    });
}, 30000); // 30 sec

// Display notification + play sound
function showMedicineNotification(name, dosage) {
  if (Notification.permission === "granted") {
    const n = new Notification("💊 Medicine Reminder", {
      body: `Time to take ${name} (${dosage})`,
      icon: "https://cdn-icons-png.flaticon.com/512/2966/2966485.png"
    });

    const sound = new Audio("/static/alarm.mp3");
    sound.play();
  }
}
