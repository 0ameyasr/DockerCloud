$('#loginForm').submit(function (e) {
    e.preventDefault();
    var formData = $(this).serialize();
    $.ajax({
        type: "POST",
        url: "/login",
        data: formData,
        dataType: "json",
        success: function (response) {
            console.log(response);
            if (response.success) {
                $('#loginModal').modal('hide');
                window.location.href = window.location.href;
            } else {
                $('#loginStatus').html(response.error);
            }
        },
        error: function (xhr, status, error) {
            console.error('AJAX Error: ', status, error);
            alert('An error occurred. Please try again.');
        }
    });
});

$('#uploadForm').submit(function (e) {
    e.preventDefault();

    var formData = new FormData(this);

    $.ajax({
        type: "POST",
        url: "/upload",
        data: formData,
        dataType: "json",
        contentType: false,
        processData: false,
        success: function (response) {
            console.log(response);
            if (response.success) {
                $('#uploadModal').modal('hide');
                alert("File uploaded successfully!");
                window.location.reload();
            } else {
                $('#uploadStatus').html(response.error);
            }
        },
        error: function (xhr, status, error) {
            console.error('AJAX Error:', status, error);
            alert('An error occurred. Please try again.');
        }
    });
});


async function loadMessages() {
    try {
      const response = await fetch('/get_messages');
      const data = await response.json();
      
      if (data.success) {
        const container = document.querySelector('.messages-container');
        
        if (!data.messages || data.messages.length === 0) {
          container.innerHTML = '<div class="alert alert-info">No messages to display</div>';
          return;
        }
        
        container.innerHTML = data.messages.map(message => `
          <div class="card mb-3 message-card" data-message-id="${message._id}">
            <div class="card-header d-flex justify-content-between align-items-center">
              <span>
                <i class="fas fa-user"></i> ${message.to === currentUser ? 'From: ' + message.from : 'To: ' + message.to}
              </span>
              <small class="text-muted">
                <i class="fas fa-clock"></i> ${message.sent}
              </small>
            </div>
            <div class="card-body">
              <h6 class="card-subtitle mb-2">
                <i class="fas fa-file"></i> File: ${message.filename}
              </h6>
              <p class="card-text">${message.reason}</p>
              ${renderMessageActions(message)}
            </div>
          </div>
        `).join('');
      } else {
        showAlert('Failed to load messages: ' + data.error, 'danger');
      }
    } catch (error) {
      showAlert('Error loading messages: ' + error, 'danger');
    }
  }
  
  function renderMessageActions(message) {
    if (message.to !== currentUser) {
      return message.processed ? 
        `<div class="alert alert-info">Request ${message.status}</div>` :
        '<div class="alert alert-info">Awaiting response</div>';
    }
    
    return message.processed ?
      `<div class="alert alert-info">Request ${message.status}</div>` :
      `<div class="btn-group">
        <button class="btn btn-success btn-sm access-response" 
                data-action="grant" 
                data-message-id="${message._id}"
                data-file="${message.file}"
                data-requester="${message.from}">
          <i class="fas fa-check"></i> Grant Access
        </button>
        <button class="btn btn-danger btn-sm access-response" 
                data-action="deny" 
                data-message-id="${message._id}"
                data-file="${message.file}"
                data-requester="${message.from}">
          <i class="fas fa-times"></i> Deny
        </button>
      </div>`;
  }
  
  async function handleRequestAccess(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    const content = formData.get('content');
    if (content.length < 20) {
      showAlert('Please provide a reason that is at least 20 characters long.', 'warning');
      return false;
    }
    
    try {
      const response = await fetch('/send_request', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        const modal = bootstrap.Modal.getInstance(form.closest('.modal'));
        modal.hide();
        showAlert('Request sent successfully!', 'success');
        form.reset();
      } else {
        showAlert(result.error || 'Failed to send request', 'danger');
      }
    } catch (error) {
      showAlert('An error occurred while sending the request', 'danger');
    }
    
    return false;
  }
  
  async function handleAccessResponse(button) {
    const messageId = button.dataset.messageId;
    const action = button.dataset.action;
    const file = button.dataset.file;
    const requester = button.dataset.requester;
    
    try {
      const response = await fetch('/handle_access', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messageId,
          action,
          file,
          requester
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        const messageCard = button.closest('.message-card');
        const buttonGroup = button.closest('.btn-group');
        buttonGroup.innerHTML = `
          <div class="alert alert-info">
            Request ${action === 'grant' ? 'accepted' : 'denied'}
          </div>
        `;
        
        showAlert(`Access ${action === 'grant' ? 'granted' : 'denied'} successfully`, 'success');
      } else {
        showAlert(result.error || 'Failed to process request', 'danger');
      }
    } catch (error) {
      showAlert('An error occurred while processing the request', 'danger');
    }
  }
  
  function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => alertDiv.remove(), 5000);
  }
  
  document.addEventListener('DOMContentLoaded', function() {
    const currentUser = document.querySelector('a[href="/logout"]')?.textContent.trim() || null;
    window.currentUser = currentUser;
  
    const messagesModal = document.getElementById('messagesModal');
    if (messagesModal) {
      messagesModal.addEventListener('show.bs.modal', loadMessages);
    }
  
    document.addEventListener('click', function(e) {
      if (e.target.classList.contains('access-response')) {
        handleAccessResponse(e.target);
      }
    });
  
    document.querySelectorAll('.request-access-form').forEach(form => {
      form.onsubmit = handleRequestAccess;
    });
  });

  function deleteFile(filePath) {
    fetch("/delete_file", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ filePath: filePath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("File deleted successfully.");
            location.reload(); 
        } else {
            alert("Error deleting file: " + data.error);
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Error deleting file.");
    });
}