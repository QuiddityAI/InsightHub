<script setup>
import httpClient from "../../api/httpClient"

import {
  ChevronLeftIcon,
} from "@heroicons/vue/24/outline"

import ClassifierClassListItem from "./ClassifierClassListItem.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/settings_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier_id"],
  emits: ["classifier_selected", "class_selected", "close"],
  data() {
    return {
      classifier: useAppStateStore().classifiers.find((classifier) => classifier.id === this.classifier_id),
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {},
  methods: {},
}
</script>

<template>
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ classifier.name }}</span>
      <div class="flex-1"></div>
    </div>

    <div class="my-2 flex items-stretch">
      <input
        ref="new_classifier_name"
        type="text"
        class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Class Name" />
      <button
        class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="create_classifier_class($refs.new_classifier_name.value); $refs.new_classifier_name.value = ''">
        Create
      </button>
    </div>

    <ul class="mt-3">
      <ClassifierClassListItem
        v-for="class_details in classifier.actual_classes"
        :key="class_details.name"
        :class_details="class_details"
        @click="$emit('class_selected', class_details.name); $emit('classifier_selected', classifier.id)">
      </ClassifierClassListItem>
    </ul>

    <div
      v-if="classifier.actual_classes.length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No Classes Yet</p>
    </div>
  </div>
</template>
