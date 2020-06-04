module.exports = {
  '**/*.py': files => [
    `isort ${files}`,
    `black ${files}`,
    "npm run api-spec",
    "npx speccy lint specs/spec.yaml"
  ]
}
