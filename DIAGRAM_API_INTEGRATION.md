# Diagram/Media Server API Integration Guide

## Overview

The MyPT backend now includes full integration with the dedicated diagram/media server. This allows students to add diagram content (text and images) to their weekly reports, which will be included in exported PDF and DOCX files.

## Architecture

```
Frontend → MyPT Backend → Diagram Media Server
         (Authentication)   (Server-to-Server API Key)
```

- **Frontend**: Makes authenticated requests to MyPT backend
- **MyPT Backend**: Acts as a proxy, handling authentication and communicating with media server
- **Diagram Media Server**: Independent Django service that stores diagram content (text + images)

## API Endpoints

All endpoints require JWT authentication (same as other MyPT API endpoints).

### 1. Get Diagram Content

**Endpoint**: `GET /api/export/diagram/{weekly_report_id}/`

**Description**: Retrieve diagram content for a specific weekly report.

**Response**:
```json
{
  "success": true,
  "data": {
    "exists": false,
    "report_reference": "123",
    "uuid": null,
    "text": "",
    "image": null,
    "images": [],
    "created_at": null,
    "updated_at": null
  }
}
```

**Example**:
```javascript
const response = await fetch('/api/export/diagram/42/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const data = await response.json();
```

### 2. Create Diagram Content

**Endpoint**: `POST /api/export/diagram/{weekly_report_id}/`

**Description**: Create new diagram content for a weekly report.

**Request Body**:
```json
{
  "text": "Additional diagram text content here..."
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "exists": true,
    "report_reference": "42",
    "uuid": "b2dfdf1f-d15f-46e6-989e-67c039263755",
    "text": "Additional diagram text content here...",
    "images": [],
    "image": null,
    "created_at": "2026-09-22T20:52:45.077679Z",
    "updated_at": "2026-09-22T20:52:45.079188Z"
  }
}
```

**Example**:
```javascript
const response = await fetch('/api/export/diagram/42/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: "Learned about circuit diagrams and component placement"
  })
});
const data = await response.json();
```

### 3. Update Diagram Text

**Endpoint**: `PUT /api/export/diagram/{weekly_report_id}/`

**Description**: Update the text content of an existing diagram (creates if doesn't exist).

**Request Body**:
```json
{
  "text": "Updated diagram text content..."
}
```

**Response**: Same as create endpoint

**Example**:
```javascript
const response = await fetch('/api/export/diagram/42/', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: "Updated: Learned about advanced circuit diagrams"
  })
});
const data = await response.json();
```

### 4. Delete Diagram Content

**Endpoint**: `DELETE /api/export/diagram/{weekly_report_id}/`

**Description**: Delete all diagram content (text + images) for a weekly report.

**Response**:
```json
{
  "success": true,
  "message": "Diagram content deleted successfully"
}
```

**Example**:
```javascript
const response = await fetch('/api/export/diagram/42/', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### 5. Upload Diagram Image

**Endpoint**: `POST /api/export/diagram/{weekly_report_id}/image/`

**Description**: Upload or replace the main diagram image for a weekly report.

**Request**: `multipart/form-data` with file field named `image`

**Response**:
```json
{
  "success": true,
  "data": {
    "success": true,
    "image": {
      "id": "uuid",
      "url": "http://localhost:8000/media/diagrams/.../image-uuid.jpg",
      "width": 1600,
      "height": 1200,
      "file_size": 12775,
      "content_type": "image/jpeg",
      "original_filename": "photo.jpg",
      "created_at": "2026-09-22T19:38:10.231818Z"
    },
    "document": {
      "exists": true,
      "report_reference": "42",
      "uuid": "...",
      "text": "...",
      "images": [...],
      "image": {...}
    }
  }
}
```

**Example**:
```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]);

const response = await fetch('/api/export/diagram/42/image/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
    // Note: Don't set Content-Type for FormData - browser sets it automatically
  },
  body: formData
});
const data = await response.json();
```

### 6. Delete Diagram Image

**Endpoint**: `DELETE /api/export/diagram/{weekly_report_id}/image/`

**Description**: Delete diagram image(s). Use query parameter `image_id` to delete specific image, otherwise deletes all.

**Query Parameters**:
- `image_id` (optional): Specific image UUID to delete

**Response**:
```json
{
  "success": true,
  "data": {
    "success": true,
    "deleted": 1,
    "document": {
      "exists": true,
      "report_reference": "42",
      "uuid": "...",
      "text": "...",
      "images": [],
      "image": null
    }
  }
}
```

**Example**:
```javascript
// Delete all images
const response = await fetch('/api/export/diagram/42/image/', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

// Delete specific image
const response = await fetch('/api/export/diagram/42/image/?image_id=uuid-here', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

## Export Integration

The diagram content is automatically included when exporting weekly reports:

### PDF Export
- **Endpoint**: `GET /api/export/weekly/{weekly_report_id}/pdf/`
- Diagram page is automatically appended after the signature section
- Images are downloaded from media server and embedded in PDF

### DOCX Export
- **Endpoint**: `GET /api/export/weekly/{weekly_report_id}/docx/`
- Diagram page is automatically appended as a separate section
- Images are downloaded from media server and embedded in DOCX

### Logbook Export
- **Endpoint**: `POST /api/export/all-weekly-reports/`
- Each weekly report includes its respective diagram page
- Maintains proper section formatting for all reports

## Frontend Implementation Suggestions

### 1. Diagram Editor Component

Create a component that allows users to:
- Add/edit text content for diagrams
- Upload images with preview
- Delete images
- Save changes

```javascript
const DiagramEditor = ({ weeklyReportId }) => {
  const [diagramData, setDiagramData] = useState(null);
  const [text, setText] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);

  // Load existing diagram data
  useEffect(() => {
    fetchDiagramData();
  }, [weeklyReportId]);

  const fetchDiagramData = async () => {
    const response = await fetch(`/api/export/diagram/${weeklyReportId}/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    setDiagramData(data.data);
    setText(data.data.text || '');
  };

  const saveText = async () => {
    setLoading(true);
    const method = diagramData?.exists ? 'PUT' : 'POST';
    const response = await fetch(`/api/export/diagram/${weeklyReportId}/`, {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text })
    });
    const data = await response.json();
    setDiagramData(data.data);
    setLoading(false);
  };

  const uploadImage = async () => {
    if (!imageFile) return;
    
    const formData = new FormData();
    formData.append('image', imageFile);
    
    const response = await fetch(`/api/export/diagram/${weeklyReportId}/image/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    const data = await response.json();
    setDiagramData(data.data.document);
    setImageFile(null);
  };

  return (
    <div className="diagram-editor">
      <textarea 
        value={text} 
        onChange={(e) => setText(e.target.value)}
        placeholder="Add diagram description..."
      />
      <button onClick={saveText} disabled={loading}>
        {loading ? 'Saving...' : 'Save Text'}
      </button>
      
      {diagramData?.image && (
        <img src={diagramData.image.url} alt="Diagram" />
      )}
      
      <input 
        type="file" 
        accept="image/*"
        onChange={(e) => setImageFile(e.target.files[0])}
      />
      <button onClick={uploadImage}>Upload Image</button>
    </div>
  );
};
```

### 2. Weekly Report Integration

Add diagram editing capability to the weekly report view:

```javascript
const WeeklyReportDetail = ({ reportId }) => {
  const [showDiagramEditor, setShowDiagramEditor] = useState(false);
  
  return (
    <div>
      <h2>Weekly Report {reportId}</h2>
      
      {/* Existing report content */}
      
      <button onClick={() => setShowDiagramEditor(!showDiagramEditor)}>
        {showDiagramEditor ? 'Hide' : 'Edit'} Diagram
      </button>
      
      {showDiagramEditor && (
        <DiagramEditor weeklyReportId={reportId} />
      )}
      
      {/* Export buttons */}
      <button onClick={() => exportPDF(reportId)}>Export PDF</button>
      <button onClick={() => exportDOCX(reportId)}>Export DOCX</button>
    </div>
  );
};
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "message": "Error description here"
}
```

Common error scenarios:
- **404**: Weekly report not found
- **403**: Insufficient permissions/tokens
- **400**: Invalid request data
- **500**: Server error (media server unavailable, etc.)

## Image Constraints

The media server enforces the following constraints:
- **Max file size**: 10 MB
- **Max dimensions**: 1600x1600 pixels (auto-scaled if larger)
- **Supported formats**: JPEG, PNG, WEBP
- **Auto-optimization**: Images are automatically optimized and re-encoded

## Testing

Use the provided test script to verify integration:

```bash
cd mypt-backend
python test_media_integration.py
```

This tests the core media client functionality without requiring authentication.

## Configuration

Ensure the backend `.env` file has:
```
MYPT_MEDIA_API_URL=http://localhost:8000
MYPT_MEDIA_API_KEY=local-dev-api-key-change-me
MYPT_MEDIA_TIMEOUT=30
```

For production, update these to point to your deployed media server.

## Security Notes

- The media server API key is never exposed to the frontend
- All requests go through the authenticated MyPT backend
- Students can only access diagrams for their own weekly reports
- Images are stored on the media server, not in the main backend

## Support

For issues or questions:
1. Check the media server logs: `mypt-media-server/logs/media-server.log`
2. Check backend logs: `mypt-backend/logs/django.log`
3. Verify both servers are running
4. Confirm API key matches between backend and media server