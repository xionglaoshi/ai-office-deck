import assert from 'node:assert/strict';
import {createWecomNames} from '../lib/wecom-name-utils.ts';
const {display}=createWecomNames({ExampleUser:'示例员工'});
assert.equal(display('责任人ExampleUser'),'责任人示例员工');
assert.equal(display('Unknown ExampleUser2 https://example.com/ExampleUser'),'Unknown ExampleUser2 https://example.com/ExampleUser');
console.log('synthetic names passed');
