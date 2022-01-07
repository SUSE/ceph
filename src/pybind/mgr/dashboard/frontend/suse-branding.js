/*
 * Copyright (C) 2022 SUSE, LLC.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 */
const fs = require('fs');
const child_process = require('child_process');

const fileReplacements = [{
  "replace": "src/app/core/layouts/login-layout/login-layout.component.html",
  "with": "src/app/core/layouts/login-layout/login-layout.component.brand.html"
},{
  "replace": "src/app/core/auth/login/login.component.html",
  "with": "src/app/core/auth/login/login.component.brand.html"
},{
  "replace": "src/app/core/navigation/navigation/navigation.component.html",
  "with": "src/app/core/navigation/navigation/navigation.component.brand.html"
},{
  "replace": "src/app/core/navigation/about/about.component.html",
  "with": "src/app/core/navigation/about/about.component.brand.html"
}];

if (process.argv.includes('--undo')) {
  undo();
} else {
  apply();
}

function apply() {
  fileReplacements.forEach((options) => {
    fs.copyFile(options.with, options.replace, (error) => {
      if (error) throw error;
      logger(`'${options.replace}' was replaced by '${options.with}'`);
    });
  });
}

function undo() {
  fileReplacements.forEach((options) => {
    child_process.execSync(`git restore ${options.replace}`);
    logger(`File '${options.replace}' restored`);
  });
}

function logger(message) {
  console.log(`[suse-branding.js] ${message}`);
}
