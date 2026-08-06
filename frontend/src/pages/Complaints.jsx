import { useMemo, useState } from "react";
import {
  Loader2,
  AlertCircle,
  Inbox,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Search,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
  Link2,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { useComplaints } from "@/hooks/useComplaints";
// Read-only hooks reused to populate the assign dialogs — these already
// exist elsewhere in the app and are not being duplicated here.
import { useProperties } from "@/hooks/useProperties";
import { useMaintenanceTeams } from "@/hooks/useMaintenanceTeams";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

const PAGE_SIZE = 8;
const EXCLUDED_FIELDS = /^id$|^created_at$|^updated_at$|^created$|^updated$|^slug$/i;

/* ------------------------------------------------------------------ */
/* Helpers — shape-detection only, nothing hardcoded to a specific API */
/* ------------------------------------------------------------------ */

function detectField(row, pattern, exclude) {
  if (!row) return undefined;
  return Object.keys(row).find(
    (key) => pattern.test(key) && !(exclude && exclude.test(key))
  );
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "object") return value.name ?? value.title ?? JSON.stringify(value);
  return String(value);
}

function statusBadgeVariant(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (/resolved|closed|completed/.test(normalized)) return "default";
  if (/pending|review|assigned/.test(normalized)) return "secondary";
  if (/open|urgent|escalated|rejected/.test(normalized)) return "destructive";
  return "outline";
}

function priorityBadgeVariant(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (/high|urgent|critical/.test(normalized)) return "destructive";
  if (/medium|moderate/.test(normalized)) return "secondary";
  return "outline";
}

function getOptionsFromList(list) {
  if (!Array.isArray(list) || list.length === 0) return [];
  const idField = detectField(list[0], /^id$/i) || "id";
  const nameField = detectField(list[0], /name|title/i) || "name";
  return list.map((item) => ({ value: String(item[idField]), label: formatCellValue(item[nameField]) }));
}

/* ------------------------------------------------------------------ */
/* Section states                                                      */
/* ------------------------------------------------------------------ */

function SectionLoading({ label = "Loading complaints..." }) {
  return (
    <div className="flex items-center justify-center gap-2 py-14 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      {label}
    </div>
  );
}

function SectionError({ error }) {
  return (
    <div
      role="alert"
      className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
    >
      <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
      {error?.message || "Something went wrong while loading complaints."}
    </div>
  );
}

function SectionEmpty({ label = "No complaints found." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center text-muted-foreground">
      <Inbox className="h-6 w-6" aria-hidden="true" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Create / Edit form dialog (shared)                                  */
/*                                                                      */
/* NOTE: useComplaints.js only exposes a read (`useComplaints`) hook —  */
/* there is no useCreateComplaint()/useUpdateComplaint() yet, even      */
/* though complaintService.createComplaint / updateComplaint already    */
/* exist. Per instructions, no hook is invented here: submission is     */
/* stubbed with a clear TODO so this is ready to wire up once those     */
/* mutation hooks are added.                                            */
/* ------------------------------------------------------------------ */

function ComplaintFormDialog({
  open,
  onOpenChange,
  title,
  description,
  initialValues,
  fields,
  onSubmit,
  submitLabel,
}) {
  const [values, setValues] = useState(initialValues);

  function handleChange(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {fields.map((field) => {
              const inputId = `complaint-${field.key}`;

              if (field.type === "select") {
                return (
                  <div key={field.key} className="grid gap-1.5">
                    <Label htmlFor={inputId} className="capitalize">
                      {field.label}
                    </Label>
                    <Select
                      value={values[field.key] ?? ""}
                      onValueChange={(value) => handleChange(field.key, value)}
                    >
                      <SelectTrigger id={inputId}>
                        <SelectValue placeholder={`Select ${field.label}`} />
                      </SelectTrigger>
                      <SelectContent>
                        {field.options.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                );
              }

              return (
                <div key={field.key} className="grid gap-1.5">
                  <Label htmlFor={inputId} className="capitalize">
                    {field.label}
                  </Label>
                  <Input
                    id={inputId}
                    value={values[field.key] ?? ""}
                    onChange={(event) => handleChange(field.key, event.target.value)}
                    required={field.required}
                  />
                </div>
              );
            })}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">{submitLabel}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Delete confirmation dialog                                          */
/* ------------------------------------------------------------------ */

function DeleteComplaintDialog({ complaint, displayName, onOpenChange, onConfirm }) {
  return (
    <Dialog open={!!complaint} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete complaint</DialogTitle>
          <DialogDescription>
            This will permanently remove{" "}
            <span className="font-medium text-foreground">{displayName}</span> from your
            records. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={() => onConfirm(complaint)}>
            Delete complaint
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Assign property / assign team dialogs                               */
/*                                                                      */
/* complaintService.assignProperty / assignTeam already exist, but no   */
/* useAssignProperty()/useAssignTeam() mutation hook wraps them yet —   */
/* submission is stubbed below rather than calling the service/axios    */
/* directly from the component.                                        */
/* ------------------------------------------------------------------ */

function AssignDialog({
  complaint,
  displayName,
  optionsQuery,
  options,
  title,
  description,
  emptyLabel,
  onOpenChange,
  onConfirm,
}) {
  const [selectedId, setSelectedId] = useState("");

  return (
    <Dialog open={!!complaint} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {description} <span className="font-medium text-foreground">{displayName}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {optionsQuery.isLoading ? (
            <SectionLoading label="Loading options..." />
          ) : optionsQuery.isError ? (
            <SectionError error={optionsQuery.error} />
          ) : options.length === 0 ? (
            <SectionEmpty label={emptyLabel} />
          ) : (
            <div className="grid gap-1.5">
              <Label>Select</Label>
              <Select value={selectedId} onValueChange={setSelectedId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose an option" />
                </SelectTrigger>
                <SelectContent>
                  {options.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!selectedId} onClick={() => onConfirm(complaint, selectedId)}>
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                            */
/* ------------------------------------------------------------------ */

export default function Complaints() {
  const complaintsQuery = useComplaints();
  const propertiesQuery = useProperties();
  const maintenanceTeamsQuery = useMaintenanceTeams();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  const [createOpen, setCreateOpen] = useState(false);
  const [editComplaint, setEditComplaint] = useState(null);
  const [deleteComplaint, setDeleteComplaint] = useState(null);
  const [assignPropertyComplaint, setAssignPropertyComplaint] = useState(null);
  const [assignTeamComplaint, setAssignTeamComplaint] = useState(null);

  const complaints = complaintsQuery.data;
  const firstRow = Array.isArray(complaints) && complaints.length > 0 ? complaints[0] : null;

  const idField = detectField(firstRow, /^id$/i) || "id";
  const subjectField = detectField(firstRow, /title|subject/i);
  const categoryField = detectField(firstRow, /category/i);
  const statusField = detectField(firstRow, /status/i);
  const priorityField = detectField(firstRow, /priority|severity/i);

  const columns = firstRow ? Object.keys(firstRow) : [];

  const statusOptions = useMemo(() => {
    if (!Array.isArray(complaints) || !statusField) return [];
    return Array.from(new Set(complaints.map((row) => row[statusField]).filter(Boolean)));
  }, [complaints, statusField]);

  const propertyOptions = useMemo(() => getOptionsFromList(propertiesQuery.data), [propertiesQuery.data]);
  const teamOptions = useMemo(() => getOptionsFromList(maintenanceTeamsQuery.data), [maintenanceTeamsQuery.data]);

  const filteredComplaints = useMemo(() => {
    if (!Array.isArray(complaints)) return [];
    return complaints.filter((row) => {
      const matchesStatus =
        statusFilter === "all" || !statusField || row[statusField] === statusFilter;
      if (!matchesStatus) return false;
      if (!search.trim()) return true;
      const term = search.trim().toLowerCase();
      return Object.values(row).some(
        (value) => typeof value === "string" && value.toLowerCase().includes(term)
      );
    });
  }, [complaints, search, statusFilter, statusField]);

  const totalPages = Math.max(1, Math.ceil(filteredComplaints.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedComplaints = filteredComplaints.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  function handleSearchChange(value) {
    setSearch(value);
    setPage(1);
  }

  function handleStatusFilterChange(value) {
    setStatusFilter(value);
    setPage(1);
  }

  const totalComplaints = Array.isArray(complaints) ? complaints.length : undefined;
  const openCount =
    statusField && Array.isArray(complaints)
      ? complaints.filter((row) => /open|urgent|escalated/i.test(String(row[statusField]))).length
      : undefined;
  const resolvedCount =
    statusField && Array.isArray(complaints)
      ? complaints.filter((row) => /resolved|closed|completed/i.test(String(row[statusField]))).length
      : undefined;
  const topCategory = useMemo(() => {
    if (!categoryField || !Array.isArray(complaints) || complaints.length === 0) return undefined;
    const counts = {};
    complaints.forEach((row) => {
      const value = row[categoryField];
      if (!value) return;
      counts[value] = (counts[value] || 0) + 1;
    });
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    return entries[0];
  }, [complaints, categoryField]);

  const dynamicFields = firstRow
    ? Object.keys(firstRow)
        .filter((key) => !EXCLUDED_FIELDS.test(key) && key !== "property" && !/propert|manager|team|assigned/i.test(key))
        .map((key) => {
          if (key === statusField) {
            return { key, label: key.replace(/_/g, " "), type: "select", options: statusOptions };
          }
          return { key, label: key.replace(/_/g, " "), type: "text", required: key === subjectField };
        })
    : [
        { key: "title", label: "Title", type: "text", required: true },
        { key: "category", label: "Category", type: "text" },
        { key: "status", label: "Status", type: "text" },
      ];

  const displayName = (complaint) => {
    if (!complaint) return "";
    if (subjectField && complaint[subjectField]) return formatCellValue(complaint[subjectField]);
    if (categoryField && complaint[categoryField]) return formatCellValue(complaint[categoryField]);
    return `Complaint #${complaint[idField] ?? "—"}`;
  };

  /* -------------------------------------------------------------- */
  /* Stub handlers — wire these up once the corresponding mutation   */
  /* hooks exist in useComplaints.js.                                 */
  /* -------------------------------------------------------------- */

  function handleCreateSubmit(values) {
    // TODO: replace with a real mutation once useCreateComplaint() exists
    // (complaintService.createComplaint is already available for this).
    console.warn("useCreateComplaint() not implemented yet — submitted values:", values);
    setCreateOpen(false);
  }

  function handleUpdateSubmit(values) {
    // TODO: replace with a real mutation once useUpdateComplaint() exists
    // (complaintService.updateComplaint is already available for this).
    console.warn("useUpdateComplaint() not implemented yet — submitted values:", {
      ...editComplaint,
      ...values,
    });
    setEditComplaint(null);
  }

  function handleConfirmDelete(complaint) {
    // TODO: replace with a real mutation once useDeleteComplaint() exists
    // (complaintService.deleteComplaint is already available for this).
    console.warn("useDeleteComplaint() not implemented yet — target:", complaint);
    setDeleteComplaint(null);
  }

  function handleConfirmAssignProperty(complaint, propertyId) {
    // TODO: replace with a real mutation once useAssignComplaintProperty()
    // exists (complaintService.assignProperty is already available).
    console.warn(
      "useAssignComplaintProperty() not implemented yet —",
      complaint,
      "-> property:",
      propertyId
    );
    setAssignPropertyComplaint(null);
  }

  function handleConfirmAssignTeam(complaint, teamId) {
    // TODO: replace with a real mutation once useAssignComplaintTeam()
    // exists (complaintService.assignTeam is already available).
    console.warn(
      "useAssignComplaintTeam() not implemented yet —",
      complaint,
      "-> team:",
      teamId
    );
    setAssignTeamComplaint(null);
  }

  return (
    <div className="flex flex-col gap-6 pb-10">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Complaints</h1>
          <p className="text-sm text-muted-foreground">
            Track, assign, and resolve complaints across all properties.
          </p>
        </div>
        <Button className="gap-2 self-start sm:self-auto" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Log complaint
        </Button>
      </div>

      {/* Statistics cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div>
              <p className="text-sm text-muted-foreground">Total complaints</p>
              <div className="mt-1 text-2xl font-semibold text-foreground">
                {complaintsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  formatCellValue(totalComplaints)
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <AlertTriangle className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div>
              <p className="text-sm text-muted-foreground">Open</p>
              <div className="mt-1 text-2xl font-semibold text-foreground">
                {complaintsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  formatCellValue(openCount)
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <Clock className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div>
              <p className="text-sm text-muted-foreground">Resolved</p>
              <div className="mt-1 text-2xl font-semibold text-foreground">
                {complaintsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  formatCellValue(resolvedCount)
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div className="min-w-0">
              <p className="text-sm text-muted-foreground">Top category</p>
              <div className="mt-1 truncate text-lg font-semibold text-foreground">
                {complaintsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : topCategory ? (
                  <span className="flex items-center gap-2">
                    <Badge variant="secondary">{topCategory[0]}</Badge>
                    <span className="text-sm font-normal text-muted-foreground">
                      {topCategory[1]}
                    </span>
                  </span>
                ) : (
                  "—"
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400">
              <Users className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Table card */}
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>All complaints</CardTitle>
            <CardDescription>Search, filter, and manage complaint records.</CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                value={search}
                onChange={(event) => handleSearchChange(event.target.value)}
                placeholder="Search complaints..."
                aria-label="Search complaints"
                className="w-full pl-8 sm:w-64"
              />
            </div>
            {statusOptions.length > 0 && (
              <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
                <SelectTrigger className="w-full sm:w-40" aria-label="Filter by status">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {statusOptions.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {complaintsQuery.isLoading ? (
            <SectionLoading />
          ) : complaintsQuery.isError ? (
            <SectionError error={complaintsQuery.error} />
          ) : filteredComplaints.length === 0 ? (
            <SectionEmpty
              label={
                search || statusFilter !== "all"
                  ? "No complaints match your search or filter."
                  : "No complaints found."
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    {columns.map((column) => (
                      <TableHead key={column} className="whitespace-nowrap capitalize">
                        {column.replace(/_/g, " ")}
                      </TableHead>
                    ))}
                    <TableHead className="w-12 text-right">
                      <span className="sr-only">Actions</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedComplaints.map((row, index) => (
                    <TableRow key={row[idField] ?? index}>
                      {columns.map((column) => {
                        const value = row[column];
                        const isStatusColumn = column === statusField;
                        const isPriorityColumn = column === priorityField;

                        return (
                          <TableCell key={column} className="whitespace-nowrap">
                            {isStatusColumn ? (
                              <Badge variant={statusBadgeVariant(value)}>
                                {formatCellValue(value)}
                              </Badge>
                            ) : isPriorityColumn ? (
                              <Badge variant={priorityBadgeVariant(value)}>
                                {formatCellValue(value)}
                              </Badge>
                            ) : (
                              formatCellValue(value)
                            )}
                          </TableCell>
                        );
                      })}
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              aria-label={`Actions for ${displayName(row)}`}
                            >
                              <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => setEditComplaint(row)}>
                              <Pencil className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setAssignPropertyComplaint(row)}>
                              <Link2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                              Assign property
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setAssignTeamComplaint(row)}>
                              <Users className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                              Assign team
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => setDeleteComplaint(row)}
                              className="text-destructive focus:text-destructive"
                            >
                              <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                    disabled={currentPage <= 1}
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                    disabled={currentPage >= totalPages}
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Create complaint dialog */}
      <ComplaintFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Log complaint"
        description="Enter the complaint's details below."
        initialValues={{}}
        fields={dynamicFields}
        onSubmit={handleCreateSubmit}
        submitLabel="Create complaint"
      />

      {/* Edit complaint dialog — remounts fresh per complaint via `key`, so
          no useEffect is needed to sync initial form values. */}
      {editComplaint && (
        <ComplaintFormDialog
          key={editComplaint[idField]}
          open={!!editComplaint}
          onOpenChange={(open) => !open && setEditComplaint(null)}
          title="Edit complaint"
          description={`Update details for ${displayName(editComplaint)}.`}
          initialValues={editComplaint}
          fields={dynamicFields}
          onSubmit={handleUpdateSubmit}
          submitLabel="Save changes"
        />
      )}

      {/* Delete confirmation dialog */}
      <DeleteComplaintDialog
        complaint={deleteComplaint}
        displayName={displayName(deleteComplaint)}
        onOpenChange={(open) => !open && setDeleteComplaint(null)}
        onConfirm={handleConfirmDelete}
      />

      {/* Assign property dialog */}
      <AssignDialog
        complaint={assignPropertyComplaint}
        displayName={displayName(assignPropertyComplaint)}
        optionsQuery={propertiesQuery}
        options={propertyOptions}
        title="Assign property"
        description="Choose a property to link to"
        emptyLabel="No properties available to assign."
        onOpenChange={(open) => !open && setAssignPropertyComplaint(null)}
        onConfirm={handleConfirmAssignProperty}
      />

      {/* Assign team dialog */}
      <AssignDialog
        complaint={assignTeamComplaint}
        displayName={displayName(assignTeamComplaint)}
        optionsQuery={maintenanceTeamsQuery}
        options={teamOptions}
        title="Assign maintenance team"
        description="Choose a team to handle"
        emptyLabel="No maintenance teams available to assign."
        onOpenChange={(open) => !open && setAssignTeamComplaint(null)}
        onConfirm={handleConfirmAssignTeam}
      />
    </div>
  );
}