import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Modal = ({ isOpen, onClose, data }) => {
  if (!isOpen) return null;

  const handleDownload = () => {
    const currentDate = new Date().toISOString().split("T")[0]; // Format: YYYY-MM-DD
    const filename = `response-${currentDate}.csv`;
  
    const csvContent = "data:text/csv;charset=utf-8," + 
      data.map(row => row.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
  
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", filename);
  
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  ;

  const rowsToDisplay = data ? data.slice(1) : []; // Exclude the header row

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <h3>Users</h3>
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th>First Name</th>
                <th>Last Name</th>
                <th>Username</th>
                <th>Password</th>
              </tr>
            </thead>
            <tbody>
              {rowsToDisplay.map((row, index) => (
                <tr key={index}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button onClick={handleDownload}>Download CSV</button>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
};

const Home = () => {
  const baseUrl = import.meta.env.VITE_API_URL;
  const navigate = useNavigate();
  const [csvData, setCsvData] = useState([]);
  const [error, setError] = useState('');
  const [coreCount, setCoreCount] = useState('');
  const [memory, setMemory] = useState('');
  const [duration, setDuration] = useState('');
  const [prefix, setPrefix] = useState('');
  const [csvFile, setCsvFile] = useState(null);
  const [responseData, setResponseData] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const accessToken = localStorage.getItem('access_token');

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file || file.type !== 'text/csv') {
      setError('Please upload a valid CSV file.');
      return;
    }
  
    setCsvFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      parseCSV(text);
    };
    reader.readAsText(file);
  };

  const parseCSV = (text) => {
    const rows = text.split('\n').map(row => row.split(','));
    setCsvData(rows);
    setError(''); // Clear any previous errors
  };

  const handleUpload = async () => {
    if (!coreCount || coreCount < 1) {
      setError('Core count must be greater than or equal to 1.');
      return;
    }
    if (!memory || memory < 512) {
      setError('Memory must be greater than or equal to 512 MB.');
      return;
    }
    if (!duration || duration < 0) {
      setError('Duration must be greater than  or equal to 0 hours.');
      return;
    }
    if (!prefix || !/^\/.*[^\/]$/.test(prefix)) {
      setError('Prefix must be an absolute path without trailing slash.');
      return;
    }

    const formData = new FormData();
    formData.append('file', csvFile);
    
    const url = new URL(`${baseUrl}/admin/csv`);
    url.searchParams.append('core_count', coreCount);
    url.searchParams.append('memory', memory);
    url.searchParams.append('duration', duration);
    url.searchParams.append('prefix', prefix);
  
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
        body: formData,
      });
  
      const result = await response.json();
      setResponseData(result);
      setIsModalOpen(true);
    } catch (err) {
      setError('An error occurred while uploading the data.');
      console.error(err);
    }

    setError(''); // Clear any previous errors
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  return (
    <div style={styles.container}>
      <button onClick={handleLogout} style={styles.logoutButton}>
        Logout
      </button>
      <h2>WebVirt Wizard</h2>
      <div style={styles.content}>
        <div style={styles.configContainer}>
          <input 
            type="file" 
            accept=".csv" 
            onChange={handleFileUpload} 
            style={styles.fileInput}
          />
          {error && <p style={styles.error}>{error}</p>}
          
          <div style={styles.inputGroup}>
            <input 
              type="number" 
              placeholder="Core Count" 
              value={coreCount}
              onChange={(e) => setCoreCount(e.target.value)}
              style={styles.textField}
              required
            />
            <input 
              type="number" 
              placeholder="Memory (MB)" 
              value={memory}
              onChange={(e) => setMemory(e.target.value)}
              style={styles.textField}
              required
            />
            <input 
              type="number" 
              placeholder="Duration (hours)" 
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              style={styles.textField}
              required
            />
            <p style={styles.description}>Use 0 to disable duration based expiry.</p>
            <input 
              type="text" 
              placeholder="home directory path" 
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              style={styles.textField}
              required
            />
            <p style={styles.description}>Enter where to create the user's home directory. Example: /mnt/ldapusers</p>
          </div>
          
          <button style={styles.uploadButton} onClick={handleUpload}>
            Upload
          </button>
        </div>

        <div style={styles.tableContainer}>
          {csvData.length > 0 && (
            <table style={styles.table}>
              <thead>
                <tr>
                  {csvData[0].map((header, index) => (
                    <th key={index}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvData.slice(1).map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        data={responseData}
      />
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    height: '100vh',
    overflow: 'hidden',
  },
  logoutButton: {
    position: 'absolute',
    top: '20px',
    right: '20px',
    padding: '10px 15px',
    backgroundColor: '#dc3545',
    color: '#fff',
    border: 'none',
    borderRadius: '3px',
    cursor: 'pointer',
  },
  content: {
    display: 'flex',
    width: '100%',
    height: '100%',
    maxWidth: '1200px',
  },
  configContainer: {
    flex: 1,
    padding: '20px',
    borderRight: '1px solid #ccc',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  fileInput: {
    margin: '20px 0',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    marginBottom: '20px',
  },
  textField: {
    padding: '10px',
    margin: '5px 0',
    border: '1px solid #ccc',
    borderRadius: '3px',
    width: '200px',
  },
  uploadButton: {
    padding: '10px 20px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '3px',
    cursor: 'pointer',
  },
  tableContainer: {
    flex: 2,
    padding: '20px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'auto',
  },
  table: {
    borderCollapse: 'collapse',
    width: '100%',
    maxWidth: '800px',
    boxShadow: '0 2px 5px rgba(0, 0, 0, 0.1)',
  },
  th: {
    backgroundColor: '#f2f2f2',
    padding: '10px',
    border: '1px solid #ccc',
  },
  td: {
    padding: '10px',
    border: '1px solid #ccc',
  },
  error: {
    color: 'red',
  },
  description: {
    marginTop: '5px',
    fontSize: '12px',
    color: '#555',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    background: 'white',
    padding: '100px',
    borderRadius: '5px',
    textAlign: 'center',
    margin: '0 auto',
    maxWidth: '500px',
    width: '100%',
  },
  preformatted: {
    whiteSpace: 'pre-wrap', // Ensures that long text wraps
    overflowX: 'auto', // Allows horizontal scrolling if necessary
    backgroundColor: '#f9f9f9', // Light background for readability
    padding: '10px',
    borderRadius: '5px',
    maxHeight: '300px', // Set a max height for scrolling
    overflowY: 'auto', // Vertical scrolling if content exceeds height
    border: '1px solid #ccc', // Light border for definition
  },
};

export default Home;
