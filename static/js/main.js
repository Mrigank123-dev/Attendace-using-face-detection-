document.addEventListener('DOMContentLoaded', () => {

    // --- Webcam Attendance Logic ---
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('canvas');
    const attendanceList = document.getElementById('attendance-list');
    const startCamBtn = document.getElementById('start-cam');
    const stopCamBtn = document.getElementById('stop-cam');
    
    let stream = null;
    let intervalId = null;
    let processing = false;

    if (startCamBtn) {
        startCamBtn.addEventListener('click', startWebcam);
    }
    if (stopCamBtn) {
        stopCamBtn.addEventListener('click', stopWebcam);
    }

    async function startWebcam() {
        if (stream) return; // Already running
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            video.srcObject = stream;
            video.play();
            startCamBtn.disabled = true;
            stopCamBtn.disabled = false;
            // Wait for video to be ready
            video.onloadedmetadata = () => {
                // Set canvas dimensions
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                // Start sending frames
                intervalId = setInterval(sendFrame, 1000); // Send 1 frame per second
                updateTodayAttendance(); // Initial load
            };
        } catch (err) {
            console.error("Error accessing webcam:", err);
            alert("Could not access webcam. Please ensure permissions are granted and try again.");
        }
    }

    function stopWebcam() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
        video.srcObject = null;
        startCamBtn.disabled = false;
        stopCamBtn.disabled = true;
        processing = false;
        // Clear canvas
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);
    }

    async function sendFrame() {
        if (processing || !stream) return; // Don't send if previous is still processing
        
        processing = true;
        const context = canvas.getContext('2d');
        // Draw video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('image', blob, 'webcam_frame.jpg');

            try {
                const response = await fetch('/api/recognize', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`Server error: ${response.statusText}`);
                }

                const data = await response.json();
                
                // Clear previous drawings
                context.clearRect(0, 0, canvas.width, canvas.height);
                context.drawImage(video, 0, 0, canvas.width, canvas.height);

                // Draw new results
                drawRecognitionResults(data.results);

                // Check if any names were marked
                const marked = data.results.some(r => r.name.includes('(Marked)'));
                if (marked) {
                    updateTodayAttendance(); // Refresh list if new person marked
                }

            } catch (err) {
                console.error('Error sending frame:', err);
            } finally {
                processing = false; // Ready for next frame
            }
        }, 'image/jpeg');
    }

    function drawRecognitionResults(results) {
        const context = canvas.getContext('2d');
        context.lineWidth = 3;
        context.font = '16px Arial';

        results.forEach(res => {
            const [top, right, bottom, left] = res.location;
            const isUnknown = res.name === 'Unknown';

            // Draw rectangle
            context.strokeStyle = isUnknown ? '#FF0000' : '#00FF00'; // Red for unknown, Green for known
            context.beginPath();
            context.rect(left, top, right - left, bottom - top);
            context.stroke();

            // Draw label background
            context.fillStyle = isUnknown ? '#FF0000' : '#00FF00';
            const text = `${res.name} (${res.confidence})`;
            const textMetrics = context.measureText(text);
            context.fillRect(left, bottom - 20, textMetrics.width + 8, 20);

            // Draw label text
            context.fillStyle = '#000000';
            context.fillText(text, left + 4, bottom - 4);
        });
    }

    async function updateTodayAttendance() {
        if (!attendanceList) return;
        try {
            const response = await fetch('/api/attendance/today');
            const data = await response.json();
            
            attendanceList.innerHTML = ''; // Clear list
            if (data.length === 0) {
                attendanceList.innerHTML = '<li class="text-gray-500">No attendance marked yet today.</li>';
            } else {
                data.forEach(rec => {
                    const li = document.createElement('li');
                    li.className = 'flex justify-between items-center p-2 border-b';
                    li.innerHTML = `
                        <span>
                            <strong class="text-indigo-600">${rec.name}</strong>
                            <span class="text-sm text-gray-500 ml-2">(${rec.student_id})</span>
                        </span>
                        <span class="text-sm font-medium text-gray-700">${rec.time}</span>
                    `;
                    attendanceList.appendChild(li);
                });
            }
        } catch (err) {
            console.error('Error fetching today\'s attendance:', err);
        }
    }

    // --- Student Management Logic ---
    const deleteButtons = document.querySelectorAll('.delete-student-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', async (e) => {
            const studentId = e.target.dataset.id;
            const studentName = e.target.dataset.name;
            
            if (confirm(`Are you sure you want to delete ${studentName}? This will remove all their images and attendance records.`)) {
                try {
                    const response = await fetch(`/students/api/students/${studentId}`, {
                        method: 'DELETE'
                    });
                    const data = await response.json();
                    if (data.success) {
                        alert(data.message);
                        window.location.reload(); // Refresh the page
                    } else {
                        alert('Error deleting student.');
                    }
                } catch (err) {
                    console.error('Delete error:', err);
                    alert('An error occurred.');
                }
            }
        });
    });

    // --- Reports Logic ---
    const reportForm = document.getElementById('report-form');
    const reportResults = document.getElementById('report-results');
    const exportCsvBtn = document.getElementById('export-csv-btn');

    if (reportForm) {
        reportForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const startDate = document.getElementById('start_date').value;
            const endDate = document.getElementById('end_date').value;

            if (!startDate || !endDate) {
                alert('Please select both a start and end date.');
                return;
            }

            try {
                const response = await fetch(`/api/reports?start_date=${startDate}&end_date=${endDate}`);
                const data = await response.json();
                
                reportResults.innerHTML = ''; // Clear previous results
                if (data.error) {
                    throw new Error(data.error);
                }
                
                if (data.length === 0) {
                    reportResults.innerHTML = '<p class="text-gray-500">No data found for this date range.</p>';
                    exportCsvBtn.classList.add('hidden');
                    return;
                }

                // Create table
                const table = document.createElement('table');
                table.className = 'min-w-full divide-y divide-gray-200 mt-4';
                table.innerHTML = `
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Student ID</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Days Present</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dates</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                    </tbody>
                `;
                const tbody = table.querySelector('tbody');
                data.forEach(rec => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap">${rec.name}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${rec.student_id}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${rec.present_count}</td>
                        <td class="px-6 py-4 text-sm text-gray-500">${rec.present_dates.join(', ') || 'N/A'}</td>
                    `;
                });
                reportResults.appendChild(table);
                exportCsvBtn.classList.remove('hidden'); // Show export button

            } catch (err) {
                console.error('Error fetching report:', err);
                reportResults.innerHTML = `<p class="text-red-500">Error: ${err.message}</p>`;
                exportCsvBtn.classList.add('hidden');
            }
        });
    }
    
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => {
            const startDate = document.getElementById('start_date').value;
            const endDate = document.getElementById('end_date').value;
            if (!startDate || !endDate) {
                alert('Please generate a report first.');
                return;
            }
            // Trigger download
            window.location.href = `/api/reports/export?start_date=${startDate}&end_date=${endDate}`;
        });
    }
});