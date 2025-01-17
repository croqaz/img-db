import logging

log = logging.getLogger('imgDB')
log.setLevel(logging.INFO)

console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(levelname)-7s %(message)s'))
log.addHandler(console)
