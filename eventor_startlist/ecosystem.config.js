module.exports = {
  apps: [{
    name: 'eventor',
    script: '/var/www/eventor/start.sh',
    interpreter: 'bash',
    cwd: '/var/www/eventor',
    restart_delay: 3000,
  }],
};
